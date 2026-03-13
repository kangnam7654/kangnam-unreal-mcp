#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonValue.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class AActor;

//-----------------------------------------------------------------------------
// FKN_MCP_ActorUtils
//-----------------------------------------------------------------------------

/// Shared utility functions for Actor operations.
class KN_MCP_EXTENSION_API FKN_MCP_ActorUtils
{
public:

	/// Find an actor in the current world by exact name.
	/// @param InActorName exact name of the actor.
	/// @return the actor, or nullptr if not found.
	static AActor* FindActorByName(const FString& InActorName);

	/// Convert an actor to a JSON value containing name, class, location, rotation, scale.
	/// @param InActor actor to convert.
	/// @return JSON value object, or FJsonValueNull if InActor is null.
	static TSharedPtr<FJsonValue> ActorToJsonValue(AActor* InActor);
};
