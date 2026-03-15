#include "KN_MCP_CommandGroup_BlueprintComponent.h"
#include "KN_MCP_BlueprintUtils.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/ActorComponent.h"
#include "Kismet2/KismetEditorUtilities.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_BlueprintComponent
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_BlueprintComponent);

FKN_MCP_CommandGroup_BlueprintComponent::FKN_MCP_CommandGroup_BlueprintComponent()
{

}

FKN_MCP_CommandGroup_BlueprintComponent::~FKN_MCP_CommandGroup_BlueprintComponent()
{
}

FString FKN_MCP_CommandGroup_BlueprintComponent::GetName() const
{
	return FString("BlueprintComponent");
}

FString FKN_MCP_CommandGroup_BlueprintComponent::GetApplicationName() const
{
	return FString("KN_MCP_EXTENSION");
}

void FKN_MCP_CommandGroup_BlueprintComponent::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_component_to_blueprint");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "remove_component_from_blueprint");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "read_components_from_blueprint");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_BlueprintComponent::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// add_component_to_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_component_to_blueprint")))
	{
		FString blueprintName;
		const FString* _blueprintNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("blueprint_name")) : nullptr;
		if (!_blueprintNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = *_blueprintNamePtr;

		FString componentClassName;
		const FString* _componentClassNamePtr = InParamsPtr->TryGetStringField(TEXT("component_class"));
		if (!_componentClassNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_class"));
		}
		componentClassName = *_componentClassNamePtr;

		// Optional parameters
		FString componentName;
		if (const FString* _componentNamePtr = InParamsPtr->TryGetStringField(TEXT("component_name")))
		{
			componentName = *_componentNamePtr;
		}

		FString parentComponentName;
		if (const FString* _parentComponentNamePtr = InParamsPtr->TryGetStringField(TEXT("parent_component")))
		{
			parentComponentName = *_parentComponentNamePtr;
		}

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
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
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unknown component class: %s"), *componentClassName));
		}

		// Ensure SCS exists
		if (!blueprint->SimpleConstructionScript)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript (not an Actor-based Blueprint?)"));
		}

		// Check for duplicate component name
		if (!componentName.IsEmpty() && FKN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component with name '%s' already exists in this Blueprint"), *componentName));
		}

		// Create SCS node
		FName nodeName = componentName.IsEmpty() ? NAME_None : FName(*componentName);
		USCS_Node* newNode = blueprint->SimpleConstructionScript->CreateNode(compClass, nodeName);
		if (!newNode)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to create SCS node"));
		}

		// Mark dirty before mutation (for correct undo recording)
		blueprint->Modify();

		// Attach to parent or add as root
		if (!parentComponentName.IsEmpty())
		{
			USCS_Node* parentNode = FKN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, parentComponentName);
			if (!parentNode)
			{
				KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Parent component not found: %s"), *parentComponentName));
			}

			parentNode->AddChildNode(newNode);
		}
		else
		{
			blueprint->SimpleConstructionScript->AddNode(newNode);
		}

		// Compile
		FKismetEditorUtilities::CompileBlueprint(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), newNode->GetVariableName().ToString());
		InResultPtr->SetStringField(TEXT("component_class"), compClass->GetName());
		if (!parentComponentName.IsEmpty())
		{
			InResultPtr->SetStringField(TEXT("parent_component"), parentComponentName);
		}
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// remove_component_from_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("remove_component_from_blueprint")))
	{
		FString blueprintName;
		const FString* _blueprintNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("blueprint_name")) : nullptr;
		if (!_blueprintNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = *_blueprintNamePtr;

		FString componentName;
		const FString* _componentNamePtr = InParamsPtr->TryGetStringField(TEXT("component_name"));
		if (!_componentNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}
		componentName = *_componentNamePtr;

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript"));
		}

		USCS_Node* targetNode = FKN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName);
		if (!targetNode)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Prevent removing the default scene root
		if (targetNode == blueprint->SimpleConstructionScript->GetDefaultSceneRootNode())
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Cannot remove the default scene root component"));
		}

		// Save component info before removal
		FString removedClassName = targetNode->ComponentTemplate ? targetNode->ComponentTemplate->GetClass()->GetName() : TEXT("Unknown");

		// Mark dirty before mutation (for correct undo recording)
		blueprint->Modify();

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

		// Compile
		FKismetEditorUtilities::CompileBlueprint(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("removed_component"), componentName);
		InResultPtr->SetStringField(TEXT("removed_class"), removedClassName);
		if (children.Num() > 0)
		{
			InResultPtr->SetNumberField(TEXT("reparented_children"), children.Num());
		}
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// read_components_from_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("read_components_from_blueprint")))
	{
		FString blueprintName;
		const FString* _blueprintNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("blueprint_name")) : nullptr;
		if (!_blueprintNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = *_blueprintNamePtr;

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		TArray<TSharedPtr<FJsonValue>> componentArray;
		if (blueprint->SimpleConstructionScript)
		{
			for (USCS_Node* node : blueprint->SimpleConstructionScript->GetAllNodes())
			{
				if (node && node->ComponentTemplate)
				{
					TSharedPtr<FJsonObject> compObj = MakeShareable(new FJsonObject());
					compObj->SetStringField(TEXT("name"), node->GetVariableName().ToString());
					compObj->SetStringField(TEXT("class"), node->ComponentTemplate->GetClass()->GetName());
					compObj->SetBoolField(TEXT("is_root"), node == blueprint->SimpleConstructionScript->GetDefaultSceneRootNode());

					// Include parent info
					FString parentName = TEXT("");
					for (USCS_Node* otherNode : blueprint->SimpleConstructionScript->GetAllNodes())
					{
						if (otherNode && otherNode != node)
						{
							for (USCS_Node* child : otherNode->GetChildNodes())
							{
								if (child == node)
								{
									parentName = otherNode->GetVariableName().ToString();
									break;
								}
							}
							if (!parentName.IsEmpty()) break;
						}
					}
					if (!parentName.IsEmpty())
					{
						compObj->SetStringField(TEXT("parent"), parentName);
					}

					componentArray.Add(MakeShareable(new FJsonValueObject(compObj)));
				}
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetNumberField(TEXT("count"), componentArray.Num());
		InResultPtr->SetArrayField(TEXT("components"), componentArray);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
