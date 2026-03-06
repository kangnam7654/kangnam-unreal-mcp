#include "WN_MCP_CommandGroup_Editor.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Editor
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Editor);

FWN_MCP_CommandGroup_Editor::FWN_MCP_CommandGroup_Editor()
{

}

FWN_MCP_CommandGroup_Editor::~FWN_MCP_CommandGroup_Editor()
{
}

FString FWN_MCP_CommandGroup_Editor::GetName() const
{
	return FString("Editor");
}

void FWN_MCP_CommandGroup_Editor::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("get_actors_in_level")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Editor::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
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

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}

TSharedPtr<FJsonValue> FWN_MCP_CommandGroup_Editor::ActorToJsonValue(AActor* InActor)
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
