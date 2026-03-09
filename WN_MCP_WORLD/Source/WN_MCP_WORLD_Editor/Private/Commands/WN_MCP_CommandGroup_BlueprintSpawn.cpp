#include "WN_MCP_CommandGroup_BlueprintSpawn.h"
#include "WN_MCP_BlueprintUtils.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_BlueprintSpawn
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_BlueprintSpawn);

FWN_MCP_CommandGroup_BlueprintSpawn::FWN_MCP_CommandGroup_BlueprintSpawn()
{

}

FWN_MCP_CommandGroup_BlueprintSpawn::~FWN_MCP_CommandGroup_BlueprintSpawn()
{

}

FString FWN_MCP_CommandGroup_BlueprintSpawn::GetName() const
{
	return FString("BlueprintSpawn");
}

void FWN_MCP_CommandGroup_BlueprintSpawn::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("spawn_blueprint_actor")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_BlueprintSpawn::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	if (InCommandName == FString(TEXT("spawn_blueprint_actor")))
	{
		// Get required parameters
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString actorName;
		if (!InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Verify GeneratedClass exists
		if (!blueprint->GeneratedClass)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint '%s' has no GeneratedClass. Compile the Blueprint first."), *blueprintName));
		}

		// Check for duplicate actor name
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

		// Optional transform parameters
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

		// Spawn the actor from Blueprint's GeneratedClass
		FActorSpawnParameters spawnParams;
		spawnParams.Name = *actorName;

		AActor* newActor = GWorld->SpawnActor<AActor>(blueprint->GeneratedClass, location, rotation, spawnParams);
		if (!newActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to spawn actor from Blueprint '%s'"), *blueprintName));
		}

		// Apply scale
		newActor->SetActorScale3D(scale);

		// Build actor JSON (inline — same format as Actor CommandGroup)
		TSharedPtr<FJsonObject> actorObject = MakeShareable(new FJsonObject());
		actorObject->SetStringField(TEXT("name"), newActor->GetName());
		actorObject->SetStringField(TEXT("class"), newActor->GetClass()->GetName());

		FVector actorLocation = newActor->GetActorLocation();
		TArray<TSharedPtr<FJsonValue>> locationJsonArray;
		locationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorLocation.X)));
		locationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorLocation.Y)));
		locationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorLocation.Z)));
		actorObject->SetArrayField(TEXT("location"), locationJsonArray);

		FRotator actorRotation = newActor->GetActorRotation();
		TArray<TSharedPtr<FJsonValue>> rotationJsonArray;
		rotationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorRotation.Pitch)));
		rotationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorRotation.Yaw)));
		rotationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorRotation.Roll)));
		actorObject->SetArrayField(TEXT("rotation"), rotationJsonArray);

		FVector actorScale = newActor->GetActorScale3D();
		TArray<TSharedPtr<FJsonValue>> scaleJsonArray;
		scaleJsonArray.Add(MakeShareable(new FJsonValueNumber(actorScale.X)));
		scaleJsonArray.Add(MakeShareable(new FJsonValueNumber(actorScale.Y)));
		scaleJsonArray.Add(MakeShareable(new FJsonValueNumber(actorScale.Z)));
		actorObject->SetArrayField(TEXT("scale"), scaleJsonArray);

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetObjectField(TEXT("actor"), actorObject);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
