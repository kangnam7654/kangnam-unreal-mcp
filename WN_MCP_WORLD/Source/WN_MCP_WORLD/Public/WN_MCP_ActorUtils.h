#pragma once

#include "CoreMinimal.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class AActor;

//-----------------------------------------------------------------------------
// FWN_MCP_ActorUtils
//-----------------------------------------------------------------------------

/// Shared utility functions for Actor operations.
class WN_MCP_WORLD_API FWN_MCP_ActorUtils
{
public:

	/// Find an actor in the current world by exact name.
	/// @param InActorName exact name of the actor.
	/// @return the actor, or nullptr if not found.
	static AActor* FindActorByName(const FString& InActorName);
};
