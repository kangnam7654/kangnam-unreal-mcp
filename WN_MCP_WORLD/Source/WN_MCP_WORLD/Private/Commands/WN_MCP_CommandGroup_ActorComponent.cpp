#include "WN_MCP_CommandGroup_ActorComponent.h"
#include "WN_MCP_ActorUtils.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "GameFramework/Actor.h"
#include "Components/ActorComponent.h"
#include "Components/SceneComponent.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_ActorComponent
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_ActorComponent);

FWN_MCP_CommandGroup_ActorComponent::FWN_MCP_CommandGroup_ActorComponent()
{

}

FWN_MCP_CommandGroup_ActorComponent::~FWN_MCP_CommandGroup_ActorComponent()
{
}

FString FWN_MCP_CommandGroup_ActorComponent::GetName() const
{
	return FString("ActorComponent");
}

FString FWN_MCP_CommandGroup_ActorComponent::GetApplicationName() const
{
	return FString("WN_MCP_WORLD");
}

void FWN_MCP_CommandGroup_ActorComponent::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_component_to_actor");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "remove_component_from_actor");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "read_components_from_actor");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_ActorComponent::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// add_component_to_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_component_to_actor")))
	{
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

		AActor* foundActor = FWN_MCP_ActorUtils::FindActorByName(actorName);
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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("actor_name"), foundActor->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), newComponent->GetName());
		InResultPtr->SetStringField(TEXT("component_class"), compClass->GetName());
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// remove_component_from_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("remove_component_from_actor")))
	{
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

		AActor* foundActor = FWN_MCP_ActorUtils::FindActorByName(actorName);
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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("actor_name"), foundActor->GetName());
		InResultPtr->SetStringField(TEXT("removed_component"), componentName);
		InResultPtr->SetStringField(TEXT("removed_class"), removedClassName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// read_components_from_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("read_components_from_actor")))
	{
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		AActor* foundActor = FWN_MCP_ActorUtils::FindActorByName(actorName);
		if (!foundActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Enumerate components
		TArray<TSharedPtr<FJsonValue>> componentArray;
		TArray<UActorComponent*> components;
		foundActor->GetComponents(components);
		for (UActorComponent* comp : components)
		{
			if (comp)
			{
				TSharedPtr<FJsonObject> compObj = MakeShareable(new FJsonObject());
				compObj->SetStringField(TEXT("name"), comp->GetName());
				compObj->SetStringField(TEXT("class"), comp->GetClass()->GetName());
				compObj->SetBoolField(TEXT("is_root"), comp == foundActor->GetRootComponent());

				// Include transform for SceneComponents
				USceneComponent* sceneComp = Cast<USceneComponent>(comp);
				if (sceneComp)
				{
					FVector location = sceneComp->GetRelativeLocation();
					TArray<TSharedPtr<FJsonValue>> locationArray;
					locationArray.Add(MakeShareable(new FJsonValueNumber(location.X)));
					locationArray.Add(MakeShareable(new FJsonValueNumber(location.Y)));
					locationArray.Add(MakeShareable(new FJsonValueNumber(location.Z)));
					compObj->SetArrayField(TEXT("relative_location"), locationArray);

					FRotator rotation = sceneComp->GetRelativeRotation();
					TArray<TSharedPtr<FJsonValue>> rotationArray;
					rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Pitch)));
					rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Yaw)));
					rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Roll)));
					compObj->SetArrayField(TEXT("relative_rotation"), rotationArray);

					FVector scale = sceneComp->GetRelativeScale3D();
					TArray<TSharedPtr<FJsonValue>> scaleArray;
					scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.X)));
					scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.Y)));
					scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.Z)));
					compObj->SetArrayField(TEXT("relative_scale"), scaleArray);
				}

				componentArray.Add(MakeShareable(new FJsonValueObject(compObj)));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("actor_name"), foundActor->GetName());
		InResultPtr->SetNumberField(TEXT("count"), componentArray.Num());
		InResultPtr->SetArrayField(TEXT("components"), componentArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
