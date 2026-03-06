#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class UBlueprint;

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Blueprint
//-----------------------------------------------------------------------------

/// Command group for Blueprint asset CRUD operations.
class FWN_MCP_CommandGroup_Blueprint : public FWN_MCP_CommandGroup
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
	FWN_MCP_CommandGroup_Blueprint();

	/// destructor.
	~FWN_MCP_CommandGroup_Blueprint();

private:

	/// Find a Blueprint asset by name or full path.
	/// @param InBlueprintName Blueprint name (e.g. "MyBP") or full path (e.g. "/Game/Blueprints/MyBP").
	/// @return Blueprint object, or nullptr if not found.
	static UBlueprint* FindBlueprintByName(const FString& InBlueprintName);
};
