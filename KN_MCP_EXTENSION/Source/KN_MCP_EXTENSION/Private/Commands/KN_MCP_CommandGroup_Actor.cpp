#include "KN_MCP_CommandGroup_Actor.h"
#include "KN_MCP_ActorUtils.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UObjectIterator.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_Actor
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_Actor);

FKN_MCP_CommandGroup_Actor::FKN_MCP_CommandGroup_Actor()
{

}

FKN_MCP_CommandGroup_Actor::~FKN_MCP_CommandGroup_Actor()
{
}

FString FKN_MCP_CommandGroup_Actor::GetName() const
{
	return FString("Actor");
}

FString FKN_MCP_CommandGroup_Actor::GetApplicationName() const
{
	return FString("KN_MCP_EXTENSION");
}

void FKN_MCP_CommandGroup_Actor::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_actors_in_level");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "find_actors_by_name");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "spawn_actor");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "delete_actor");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "set_actor_transform");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "read_actor_content");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_Actor::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// get_actors_in_level
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_actors_in_level")))
	{
		if (GWorld == nullptr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("No world available"));
		}

		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

		TArray<TSharedPtr<FJsonValue>> jsonActorValues;
		for (AActor* actor : allActors)
		{
			if (actor)
			{
				jsonActorValues.Add(FKN_MCP_ActorUtils::ActorToJsonValue(actor));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), jsonActorValues.Num());
		InResultPtr->SetArrayField(TEXT("actors"), jsonActorValues);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// find_actors_by_name
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("find_actors_by_name")))
	{
		if (GWorld == nullptr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("No world available"));
		}

		FString searchText;
		const FString* _searchTextPtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("search_text")) : nullptr;
		if (!_searchTextPtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: search_text"));
		}
		searchText = *_searchTextPtr;

		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

		TArray<TSharedPtr<FJsonValue>> jsonActorValues;
		for (AActor* actor : allActors)
		{
			if (actor && actor->GetName().Contains(searchText))
			{
				jsonActorValues.Add(FKN_MCP_ActorUtils::ActorToJsonValue(actor));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), jsonActorValues.Num());
		InResultPtr->SetArrayField(TEXT("actors"), jsonActorValues);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// spawn_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("spawn_actor")))
	{
		if (GWorld == nullptr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("No world available"));
		}

		FString actorType;
		const FString* _actorTypePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("type")) : nullptr;
		if (!_actorTypePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: type"));
		}
		actorType = *_actorTypePtr;

		FString actorName;
		const FString* _actorNamePtr = InParamsPtr->TryGetStringField(TEXT("name"));
		if (!_actorNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}
		actorName = *_actorNamePtr;

		// optional transform parameters
		FVector location(0.0f, 0.0f, 0.0f);
		FRotator rotation(0.0f, 0.0f, 0.0f);
		FVector scale(1.0f, 1.0f, 1.0f);

		if (InParamsPtr->HasField(TEXT("location")))
		{
			const TArray<TSharedPtr<FJsonValue>>* _locationArrayPtr = InParamsPtr->TryGetArrayField(TEXT("location"));
			if (_locationArrayPtr && _locationArrayPtr->Num() >= 3)
			{
				location.X = (*_locationArrayPtr)[0]->AsNumber();
				location.Y = (*_locationArrayPtr)[1]->AsNumber();
				location.Z = (*_locationArrayPtr)[2]->AsNumber();
			}
		}

		if (InParamsPtr->HasField(TEXT("rotation")))
		{
			const TArray<TSharedPtr<FJsonValue>>* _rotationArrayPtr = InParamsPtr->TryGetArrayField(TEXT("rotation"));
			if (_rotationArrayPtr && _rotationArrayPtr->Num() >= 3)
			{
				rotation.Pitch = (*_rotationArrayPtr)[0]->AsNumber();
				rotation.Yaw = (*_rotationArrayPtr)[1]->AsNumber();
				rotation.Roll = (*_rotationArrayPtr)[2]->AsNumber();
			}
		}

		if (InParamsPtr->HasField(TEXT("scale")))
		{
			const TArray<TSharedPtr<FJsonValue>>* _scaleArrayPtr = InParamsPtr->TryGetArrayField(TEXT("scale"));
			if (_scaleArrayPtr && _scaleArrayPtr->Num() >= 3)
			{
				scale.X = (*_scaleArrayPtr)[0]->AsNumber();
				scale.Y = (*_scaleArrayPtr)[1]->AsNumber();
				scale.Z = (*_scaleArrayPtr)[2]->AsNumber();
			}
		}

		// Check for duplicate name
		if (FKN_MCP_ActorUtils::FindActorByName(actorName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor with name '%s' already exists"), *actorName));
		}

		// find UClass by type name
		UClass* actorClass = LoadClass<AActor>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *actorType));
		if (!actorClass)
		{
			// Search all loaded UClasses by short name
			for (TObjectIterator<UClass> It; It; ++It)
			{
				if (It->IsChildOf(AActor::StaticClass()) && It->GetName() == actorType)
				{
					actorClass = *It;
					break;
				}
			}
		}
		if (!actorClass)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unknown actor type: %s"), *actorType));
		}

		FActorSpawnParameters spawnParams;
		spawnParams.Name = *actorName;

		AActor* newActor = GWorld->SpawnActor<AActor>(actorClass, location, rotation, spawnParams);
		if (!newActor)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to spawn actor"));
		}

		// apply scale
		newActor->SetActorScale3D(scale);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetField(TEXT("actor"), FKN_MCP_ActorUtils::ActorToJsonValue(newActor));
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// delete_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("delete_actor")))
	{
		if (GWorld == nullptr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("No world available"));
		}

		FString actorName;
		const FString* _actorNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("name")) : nullptr;
		if (!_actorNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}
		actorName = *_actorNamePtr;

		AActor* foundActor = FKN_MCP_ActorUtils::FindActorByName(actorName);
		if (!foundActor)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Rename actor before destruction to free up the name for immediate reuse
		FName uniqueName = MakeUniqueObjectName(foundActor->GetOuter(), foundActor->GetClass(), FName(TEXT("DELETED")));
		foundActor->Rename(*uniqueName.ToString());

		GWorld->DestroyActor(foundActor);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("deleted_actor"), actorName);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// set_actor_transform
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("set_actor_transform")))
	{
		if (GWorld == nullptr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("No world available"));
		}

		FString actorName;
		const FString* _actorNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("name")) : nullptr;
		if (!_actorNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}
		actorName = *_actorNamePtr;

		AActor* foundActor = FKN_MCP_ActorUtils::FindActorByName(actorName);
		if (!foundActor)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Apply only provided transform components
		if (InParamsPtr->HasField(TEXT("location")))
		{
			const TArray<TSharedPtr<FJsonValue>>* _locationArrayPtr = InParamsPtr->TryGetArrayField(TEXT("location"));
			if (_locationArrayPtr && _locationArrayPtr->Num() >= 3)
			{
				FVector location;
				location.X = (*_locationArrayPtr)[0]->AsNumber();
				location.Y = (*_locationArrayPtr)[1]->AsNumber();
				location.Z = (*_locationArrayPtr)[2]->AsNumber();
				foundActor->SetActorLocation(location);
			}
		}

		if (InParamsPtr->HasField(TEXT("rotation")))
		{
			const TArray<TSharedPtr<FJsonValue>>* _rotationArrayPtr = InParamsPtr->TryGetArrayField(TEXT("rotation"));
			if (_rotationArrayPtr && _rotationArrayPtr->Num() >= 3)
			{
				FRotator rotation;
				rotation.Pitch = (*_rotationArrayPtr)[0]->AsNumber();
				rotation.Yaw = (*_rotationArrayPtr)[1]->AsNumber();
				rotation.Roll = (*_rotationArrayPtr)[2]->AsNumber();
				foundActor->SetActorRotation(rotation);
			}
		}

		if (InParamsPtr->HasField(TEXT("scale")))
		{
			const TArray<TSharedPtr<FJsonValue>>* _scaleArrayPtr = InParamsPtr->TryGetArrayField(TEXT("scale"));
			if (_scaleArrayPtr && _scaleArrayPtr->Num() >= 3)
			{
				FVector scale;
				scale.X = (*_scaleArrayPtr)[0]->AsNumber();
				scale.Y = (*_scaleArrayPtr)[1]->AsNumber();
				scale.Z = (*_scaleArrayPtr)[2]->AsNumber();
				foundActor->SetActorScale3D(scale);
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetField(TEXT("actor"), FKN_MCP_ActorUtils::ActorToJsonValue(foundActor));
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// read_actor_content
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("read_actor_content")))
	{
		if (GWorld == nullptr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("No world available"));
		}

		FString actorName;
		const FString* _actorNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("name")) : nullptr;
		if (!_actorNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}
		actorName = *_actorNamePtr;

		AActor* foundActor = FKN_MCP_ActorUtils::FindActorByName(actorName);
		if (!foundActor)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetField(TEXT("actor"), FKN_MCP_ActorUtils::ActorToJsonValue(foundActor));
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
