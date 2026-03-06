#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class AActor;

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Editor
//-----------------------------------------------------------------------------

/// Command group for UE editor operations (actors, viewport, etc.).
class FWN_MCP_CommandGroup_Editor : public FWN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Overrides FWN_MCP_CommandGroup
	//-------------------------------------------------------------------------

public:

	/// Get command group name.
	FString GetName() const override;

	/// Register commands.
	void OnRegisterCommands(TArray<FString>& InOutCommandNames) const override;

	/// Execute command.
	TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	FWN_MCP_CommandGroup_Editor();

	/// destructor.
	~FWN_MCP_CommandGroup_Editor();

private:

	/// Convert an actor to a JSON value containing name, class, location, rotation, scale.
	/// @param InActor actor to convert.
	/// @return JSON value representing the actor.
	static TSharedPtr<FJsonValue> ActorToJsonValue(AActor* InActor);
};
