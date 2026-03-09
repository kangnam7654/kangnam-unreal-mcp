#include "WN_MCP_CommandGroup_Actor.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Components/ActorComponent.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Actor
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Actor);

FWN_MCP_CommandGroup_Actor::FWN_MCP_CommandGroup_Actor()
{

}

FWN_MCP_CommandGroup_Actor::~FWN_MCP_CommandGroup_Actor()
{
}

FString FWN_MCP_CommandGroup_Actor::GetName() const
{
	return FString("Actor");
}

void FWN_MCP_CommandGroup_Actor::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("get_actors_in_level")));
	InOutCommandNames.Add(FString(TEXT("find_actors_by_name")));
	InOutCommandNames.Add(FString(TEXT("spawn_actor")));
	InOutCommandNames.Add(FString(TEXT("delete_actor")));
	InOutCommandNames.Add(FString(TEXT("set_actor_transform")));
	InOutCommandNames.Add(FString(TEXT("read_actor_content")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Actor::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	if (InCommandName == FString(TEXT("get_actors_in_level")))
	{
		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

		TArray<TSharedPtr<FJsonValue>> jsonActorValues;
		for (AActor* actor : allActors)
		{
			if (actor)
			{
				jsonActorValues.Add(ActorToJsonValue(actor));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), jsonActorValues.Num());
		InResultPtr->SetArrayField(TEXT("actors"), jsonActorValues);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("find_actors_by_name")))
	{
		FString searchText;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("search_text"), searchText))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: search_text"));
		}

		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

		TArray<TSharedPtr<FJsonValue>> jsonActorValues;
		for (AActor* actor : allActors)
		{
			if (actor && actor->GetName().Contains(searchText))
			{
				jsonActorValues.Add(ActorToJsonValue(actor));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), jsonActorValues.Num());
		InResultPtr->SetArrayField(TEXT("actors"), jsonActorValues);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("spawn_actor")))
	{
		FString actorType;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("type"), actorType))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: type"));
		}

		FString actorName;
		if (!InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		// optional transform parameters
		FVector location(0.0f, 0.0f, 0.0f);
		FRotator rotation(0.0f, 0.0f, 0.0f);
		FVector scale(1.0f, 1.0f, 1.0f);

		if (InParamsPtr->HasField(TEXT("location")))
		{
			const TArray<TSharedPtr<FJsonValue>>* locationArray;
			if (InParamsPtr->TryGetArrayField(TEXT("location"), locationArray) && locationArray->Num() >= 3)
			{
				location.X = (*locationArray)[0]->AsNumber();
				location.Y = (*locationArray)[1]->AsNumber();
				location.Z = (*locationArray)[2]->AsNumber();
			}
		}

		if (InParamsPtr->HasField(TEXT("rotation")))
		{
			const TArray<TSharedPtr<FJsonValue>>* rotationArray;
			if (InParamsPtr->TryGetArrayField(TEXT("rotation"), rotationArray) && rotationArray->Num() >= 3)
			{
				rotation.Pitch = (*rotationArray)[0]->AsNumber();
				rotation.Yaw = (*rotationArray)[1]->AsNumber();
				rotation.Roll = (*rotationArray)[2]->AsNumber();
			}
		}

		if (InParamsPtr->HasField(TEXT("scale")))
		{
			const TArray<TSharedPtr<FJsonValue>>* scaleArray;
			if (InParamsPtr->TryGetArrayField(TEXT("scale"), scaleArray) && scaleArray->Num() >= 3)
			{
				scale.X = (*scaleArray)[0]->AsNumber();
				scale.Y = (*scaleArray)[1]->AsNumber();
				scale.Z = (*scaleArray)[2]->AsNumber();
			}
		}

		// check for duplicate name
		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);
		for (AActor* actor : allActors)
		{
			if (actor && actor->GetName() == actorName)
			{
				WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Actor with name '%s' already exists"), *actorName));
			}
		}

		// find UClass by type name
		UClass* actorClass = LoadClass<AActor>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *actorType));
		if (!actorClass)
		{
			actorClass = LoadClass<AActor>(nullptr, *FString::Printf(TEXT("/Script/CoreUObject.%s"), *actorType));
		}
		if (!actorClass)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unknown actor type: %s"), *actorType));
		}

		FActorSpawnParameters spawnParams;
		spawnParams.Name = *actorName;

		AActor* newActor = GWorld->SpawnActor<AActor>(actorClass, location, rotation, spawnParams);
		if (!newActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to spawn actor"));
		}

		// apply scale
		newActor->SetActorScale3D(scale);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetField(TEXT("actor"), ActorToJsonValue(newActor));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("delete_actor")))
	{
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

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

		GWorld->DestroyActor(foundActor);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("deleted_actor"), actorName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("set_actor_transform")))
	{
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		// find actor by name
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

		// apply only provided transform components
		if (InParamsPtr->HasField(TEXT("location")))
		{
			const TArray<TSharedPtr<FJsonValue>>* locationArray;
			if (InParamsPtr->TryGetArrayField(TEXT("location"), locationArray) && locationArray->Num() >= 3)
			{
				FVector location;
				location.X = (*locationArray)[0]->AsNumber();
				location.Y = (*locationArray)[1]->AsNumber();
				location.Z = (*locationArray)[2]->AsNumber();
				foundActor->SetActorLocation(location);
			}
		}

		if (InParamsPtr->HasField(TEXT("rotation")))
		{
			const TArray<TSharedPtr<FJsonValue>>* rotationArray;
			if (InParamsPtr->TryGetArrayField(TEXT("rotation"), rotationArray) && rotationArray->Num() >= 3)
			{
				FRotator rotation;
				rotation.Pitch = (*rotationArray)[0]->AsNumber();
				rotation.Yaw = (*rotationArray)[1]->AsNumber();
				rotation.Roll = (*rotationArray)[2]->AsNumber();
				foundActor->SetActorRotation(rotation);
			}
		}

		if (InParamsPtr->HasField(TEXT("scale")))
		{
			const TArray<TSharedPtr<FJsonValue>>* scaleArray;
			if (InParamsPtr->TryGetArrayField(TEXT("scale"), scaleArray) && scaleArray->Num() >= 3)
			{
				FVector scale;
				scale.X = (*scaleArray)[0]->AsNumber();
				scale.Y = (*scaleArray)[1]->AsNumber();
				scale.Z = (*scaleArray)[2]->AsNumber();
				foundActor->SetActorScale3D(scale);
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetField(TEXT("actor"), ActorToJsonValue(foundActor));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	if (InCommandName == FString(TEXT("read_actor_content")))
	{
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		// find actor by name
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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());

		// basic info (same as ActorToJsonValue)
		InResultPtr->SetStringField(TEXT("name"), foundActor->GetName());
		InResultPtr->SetStringField(TEXT("class"), foundActor->GetClass()->GetName());

		// location
		FVector location = foundActor->GetActorLocation();
		TArray<TSharedPtr<FJsonValue>> locationArray;
		locationArray.Add(MakeShareable(new FJsonValueNumber(location.X)));
		locationArray.Add(MakeShareable(new FJsonValueNumber(location.Y)));
		locationArray.Add(MakeShareable(new FJsonValueNumber(location.Z)));
		InResultPtr->SetArrayField(TEXT("location"), locationArray);

		// rotation
		FRotator rotation = foundActor->GetActorRotation();
		TArray<TSharedPtr<FJsonValue>> rotationArray;
		rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Pitch)));
		rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Yaw)));
		rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Roll)));
		InResultPtr->SetArrayField(TEXT("rotation"), rotationArray);

		// scale
		FVector actorScale = foundActor->GetActorScale3D();
		TArray<TSharedPtr<FJsonValue>> scaleArray;
		scaleArray.Add(MakeShareable(new FJsonValueNumber(actorScale.X)));
		scaleArray.Add(MakeShareable(new FJsonValueNumber(actorScale.Y)));
		scaleArray.Add(MakeShareable(new FJsonValueNumber(actorScale.Z)));
		InResultPtr->SetArrayField(TEXT("scale"), scaleArray);

		// components
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
				componentArray.Add(MakeShareable(new FJsonValueObject(compObj)));
			}
		}
		InResultPtr->SetNumberField(TEXT("component_count"), componentArray.Num());
		InResultPtr->SetArrayField(TEXT("components"), componentArray);

		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}

TSharedPtr<FJsonValue> FWN_MCP_CommandGroup_Actor::ActorToJsonValue(AActor* InActor)
{
	if (!InActor)
	{
		return MakeShareable(new FJsonValueNull());
	}

	TSharedPtr<FJsonObject> actorObject = MakeShareable(new FJsonObject());
	actorObject->SetStringField(TEXT("name"), InActor->GetName());
	actorObject->SetStringField(TEXT("class"), InActor->GetClass()->GetName());

	// location
	FVector location = InActor->GetActorLocation();
	TArray<TSharedPtr<FJsonValue>> locationArray;
	locationArray.Add(MakeShareable(new FJsonValueNumber(location.X)));
	locationArray.Add(MakeShareable(new FJsonValueNumber(location.Y)));
	locationArray.Add(MakeShareable(new FJsonValueNumber(location.Z)));
	actorObject->SetArrayField(TEXT("location"), locationArray);

	// rotation
	FRotator rotation = InActor->GetActorRotation();
	TArray<TSharedPtr<FJsonValue>> rotationArray;
	rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Pitch)));
	rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Yaw)));
	rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Roll)));
	actorObject->SetArrayField(TEXT("rotation"), rotationArray);

	// scale
	FVector scale = InActor->GetActorScale3D();
	TArray<TSharedPtr<FJsonValue>> scaleArray;
	scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.X)));
	scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.Y)));
	scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.Z)));
	actorObject->SetArrayField(TEXT("scale"), scaleArray);

	return MakeShareable(new FJsonValueObject(actorObject));
}
