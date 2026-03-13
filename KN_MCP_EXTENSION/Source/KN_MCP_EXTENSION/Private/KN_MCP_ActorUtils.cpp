#include "KN_MCP_ActorUtils.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

//-----------------------------------------------------------------------------
// FKN_MCP_ActorUtils
//-----------------------------------------------------------------------------

AActor* FKN_MCP_ActorUtils::FindActorByName(const FString& InActorName)
{
	if (!GWorld)
	{
		return nullptr;
	}

	TArray<AActor*> allActors;
	UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

	for (AActor* actor : allActors)
	{
		if (actor && actor->GetName() == InActorName)
		{
			return actor;
		}
	}

	return nullptr;
}

TSharedPtr<FJsonValue> FKN_MCP_ActorUtils::ActorToJsonValue(AActor* InActor)
{
	if (!InActor)
	{
		return MakeShareable(new FJsonValueNull());
	}

	TSharedPtr<FJsonObject> actorObject = MakeShareable(new FJsonObject());
	actorObject->SetStringField(TEXT("name"), InActor->GetName());
	actorObject->SetStringField(TEXT("class"), InActor->GetClass()->GetName());

	// Location
	FVector location = InActor->GetActorLocation();
	TArray<TSharedPtr<FJsonValue>> locationArray;
	locationArray.Add(MakeShareable(new FJsonValueNumber(location.X)));
	locationArray.Add(MakeShareable(new FJsonValueNumber(location.Y)));
	locationArray.Add(MakeShareable(new FJsonValueNumber(location.Z)));
	actorObject->SetArrayField(TEXT("location"), locationArray);

	// Rotation
	FRotator rotation = InActor->GetActorRotation();
	TArray<TSharedPtr<FJsonValue>> rotationArray;
	rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Pitch)));
	rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Yaw)));
	rotationArray.Add(MakeShareable(new FJsonValueNumber(rotation.Roll)));
	actorObject->SetArrayField(TEXT("rotation"), rotationArray);

	// Scale
	FVector scale = InActor->GetActorScale3D();
	TArray<TSharedPtr<FJsonValue>> scaleArray;
	scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.X)));
	scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.Y)));
	scaleArray.Add(MakeShareable(new FJsonValueNumber(scale.Z)));
	actorObject->SetArrayField(TEXT("scale"), scaleArray);

	return MakeShareable(new FJsonValueObject(actorObject));
}
