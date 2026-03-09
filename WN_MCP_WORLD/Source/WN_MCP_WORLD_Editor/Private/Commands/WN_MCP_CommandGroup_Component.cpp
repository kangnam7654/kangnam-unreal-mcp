#include "WN_MCP_CommandGroup_Component.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/ActorComponent.h"
#include "Components/SceneComponent.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Component
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Component);

FWN_MCP_CommandGroup_Component::FWN_MCP_CommandGroup_Component()
{

}

FWN_MCP_CommandGroup_Component::~FWN_MCP_CommandGroup_Component()
{
}

FString FWN_MCP_CommandGroup_Component::GetName() const
{
	return FString("Component");
}

void FWN_MCP_CommandGroup_Component::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("add_component_to_blueprint")));
	InOutCommandNames.Add(FString(TEXT("remove_component_from_blueprint")));
	InOutCommandNames.Add(FString(TEXT("add_component_to_actor")));
	InOutCommandNames.Add(FString(TEXT("remove_component_from_actor")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Component::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	if (InCommandName == FString(TEXT("add_component_to_blueprint")))
	{
		// Get required parameters
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString componentClassName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_class"), componentClassName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_class"));
		}

		// Optional parameters
		FString componentName;
		InParamsPtr->TryGetStringField(TEXT("component_name"), componentName);

		FString parentComponentName;
		InParamsPtr->TryGetStringField(TEXT("parent_component"), parentComponentName);

		// Find blueprint
		UBlueprint* blueprint = FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Find component class
		UClass* compClass = LoadClass<UActorComponent>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *componentClassName));
		if (!compClass)
		{
			compClass = LoadClass<UActorComponent>(nullptr, *FString::Printf(TEXT("/Script/CoreUObject.%s"), *componentClassName));
		}
		if (!compClass)
		{
			// Try with U prefix stripped (in case user passed "UStaticMeshComponent")
			FString strippedName = componentClassName;
			if (strippedName.StartsWith(TEXT("U")))
			{
				strippedName = strippedName.RightChop(1);
				compClass = LoadClass<UActorComponent>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *strippedName));
			}
		}
		if (!compClass)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unknown component class: %s"), *componentClassName));
		}

		// Ensure SCS exists
		if (!blueprint->SimpleConstructionScript)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript (not an Actor-based Blueprint?)"));
		}

		// Check for duplicate component name
		if (!componentName.IsEmpty())
		{
			for (USCS_Node* existingNode : blueprint->SimpleConstructionScript->GetAllNodes())
			{
				if (existingNode && existingNode->GetVariableName().ToString() == componentName)
				{
					WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
						*FString::Printf(TEXT("Component with name '%s' already exists in this Blueprint"), *componentName));
				}
			}
		}

		// Create SCS node
		FName nodeName = componentName.IsEmpty() ? NAME_None : FName(*componentName);
		USCS_Node* newNode = blueprint->SimpleConstructionScript->CreateNode(compClass, nodeName);
		if (!newNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to create SCS node"));
		}

		// Attach to parent or add as root
		if (!parentComponentName.IsEmpty())
		{
			USCS_Node* parentNode = nullptr;
			for (USCS_Node* node : blueprint->SimpleConstructionScript->GetAllNodes())
			{
				if (node && node->GetVariableName().ToString() == parentComponentName)
				{
					parentNode = node;
					break;
				}
			}

			if (!parentNode)
			{
				WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Parent component not found: %s"), *parentComponentName));
			}

			parentNode->AddChildNode(newNode);
		}
		else
		{
			blueprint->SimpleConstructionScript->AddNode(newNode);
		}

		// Mark dirty and compile
		blueprint->Modify();
		FKismetEditorUtilities::CompileBlueprint(blueprint);

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), newNode->GetVariableName().ToString());
		InResultPtr->SetStringField(TEXT("component_class"), compClass->GetName());
		if (!parentComponentName.IsEmpty())
		{
			InResultPtr->SetStringField(TEXT("parent_component"), parentComponentName);
		}
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("remove_component_from_blueprint")))
	{
		// Get required parameters
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString componentName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_name"), componentName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}

		// Find blueprint
		UBlueprint* blueprint = FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript"));
		}

		// Find the target node
		USCS_Node* targetNode = nullptr;
		for (USCS_Node* node : blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (node && node->GetVariableName().ToString() == componentName)
			{
				targetNode = node;
				break;
			}
		}

		if (!targetNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Prevent removing the default scene root
		if (targetNode == blueprint->SimpleConstructionScript->GetDefaultSceneRootNode())
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Cannot remove the default scene root component"));
		}

		// Save component info before removal
		FString removedClassName = targetNode->ComponentTemplate ? targetNode->ComponentTemplate->GetClass()->GetName() : TEXT("Unknown");

		// Find parent node (if any)
		USCS_Node* parentNode = nullptr;
		for (USCS_Node* node : blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (node && node != targetNode)
			{
				for (USCS_Node* child : node->GetChildNodes())
				{
					if (child == targetNode)
					{
						parentNode = node;
						break;
					}
				}
				if (parentNode) break;
			}
		}

		// Re-parent children before removal
		TArray<USCS_Node*> children = targetNode->GetChildNodes();
		for (USCS_Node* child : children)
		{
			targetNode->RemoveChildNode(child);
			if (parentNode)
			{
				parentNode->AddChildNode(child);
			}
			else
			{
				blueprint->SimpleConstructionScript->AddNode(child);
			}
		}

		// Remove the target node from SCS
		blueprint->SimpleConstructionScript->RemoveNode(targetNode);

		// Mark dirty and compile
		blueprint->Modify();
		FKismetEditorUtilities::CompileBlueprint(blueprint);

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("removed_component"), componentName);
		InResultPtr->SetStringField(TEXT("removed_class"), removedClassName);
		if (children.Num() > 0)
		{
			InResultPtr->SetNumberField(TEXT("reparented_children"), children.Num());
		}
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("add_component_to_actor")))
	{
		// Get required parameters
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		FString componentClassName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_class"), componentClassName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_class"));
		}

		// Optional component name
		FString componentName;
		InParamsPtr->TryGetStringField(TEXT("component_name"), componentName);

		// Find actor by name
		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

		AActor* foundActor = nullptr;
		for (AActor* actor : allActors)
		{
			if (actor && actor->GetName() == actorName)
			{
				foundActor = actor;
				break;
			}
		}

		if (!foundActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Find component class
		UClass* compClass = LoadClass<UActorComponent>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *componentClassName));
		if (!compClass)
		{
			compClass = LoadClass<UActorComponent>(nullptr, *FString::Printf(TEXT("/Script/CoreUObject.%s"), *componentClassName));
		}
		if (!compClass)
		{
			FString strippedName = componentClassName;
			if (strippedName.StartsWith(TEXT("U")))
			{
				strippedName = strippedName.RightChop(1);
				compClass = LoadClass<UActorComponent>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *strippedName));
			}
		}
		if (!compClass)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unknown component class: %s"), *componentClassName));
		}

		// Create the component
		FName compName = componentName.IsEmpty() ? MakeUniqueObjectName(foundActor, compClass) : FName(*componentName);
		UActorComponent* newComponent = NewObject<UActorComponent>(foundActor, compClass, compName);
		if (!newComponent)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to create component"));
		}

		// If it's a SceneComponent, attach to root
		USceneComponent* sceneComponent = Cast<USceneComponent>(newComponent);
		if (sceneComponent && foundActor->GetRootComponent())
		{
			sceneComponent->SetupAttachment(foundActor->GetRootComponent());
		}
		else if (sceneComponent && !foundActor->GetRootComponent())
		{
			foundActor->SetRootComponent(sceneComponent);
		}

		// Register the component to activate it
		newComponent->RegisterComponent();

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("actor_name"), foundActor->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), newComponent->GetName());
		InResultPtr->SetStringField(TEXT("component_class"), compClass->GetName());
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("remove_component_from_actor")))
	{
		// Get required parameters
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		FString componentName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_name"), componentName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}

		// Find actor by name
		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

		AActor* foundActor = nullptr;
		for (AActor* actor : allActors)
		{
			if (actor && actor->GetName() == actorName)
			{
				foundActor = actor;
				break;
			}
		}

		if (!foundActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Find the component by name
		UActorComponent* targetComponent = nullptr;
		TArray<UActorComponent*> components;
		foundActor->GetComponents(components);
		for (UActorComponent* comp : components)
		{
			if (comp && comp->GetName() == componentName)
			{
				targetComponent = comp;
				break;
			}
		}

		if (!targetComponent)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component '%s' not found on actor '%s'"), *componentName, *actorName));
		}

		// Prevent removing root component
		if (targetComponent == foundActor->GetRootComponent())
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Cannot remove the root component. Delete the actor instead."));
		}

		// Save info before destruction
		FString removedClassName = targetComponent->GetClass()->GetName();

		// Destroy the component
		targetComponent->DestroyComponent();

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("actor_name"), foundActor->GetName());
		InResultPtr->SetStringField(TEXT("removed_component"), componentName);
		InResultPtr->SetStringField(TEXT("removed_class"), removedClassName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}

UBlueprint* FWN_MCP_CommandGroup_Component::FindBlueprintByName(const FString& InBlueprintName)
{
	FString objectPath;

	// Check if it's already a full path
	if (InBlueprintName.StartsWith(TEXT("/")))
	{
		FString assetName = FPaths::GetBaseFilename(InBlueprintName);
		objectPath = FString::Printf(TEXT("%s.%s"), *InBlueprintName, *assetName);
	}
	else
	{
		objectPath = FString::Printf(TEXT("/Game/Blueprints/%s.%s"), *InBlueprintName, *InBlueprintName);
	}

	// Try direct load first
	UBlueprint* blueprint = LoadObject<UBlueprint>(nullptr, *objectPath);
	if (blueprint)
	{
		return blueprint;
	}

	// Try asset registry
	FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
	FAssetData assetData = assetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(objectPath));

	if (assetData.IsValid())
	{
		blueprint = Cast<UBlueprint>(assetData.GetAsset());
		if (blueprint)
		{
			return blueprint;
		}
	}

	// Fallback: in-memory search
	FString packagePath = TEXT("/Game/Blueprints/") + InBlueprintName;
	blueprint = FindObject<UBlueprint>(nullptr, *packagePath);

	return blueprint;
}
