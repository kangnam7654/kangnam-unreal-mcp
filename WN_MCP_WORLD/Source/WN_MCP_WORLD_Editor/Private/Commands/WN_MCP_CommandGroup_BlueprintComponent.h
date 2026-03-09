#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_BlueprintComponent
//-----------------------------------------------------------------------------

/// Command group for Blueprint SCS component operations (add/remove/read).
class FWN_MCP_CommandGroup_BlueprintComponent : public FWN_MCP_CommandGroup
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
	FWN_MCP_CommandGroup_BlueprintComponent();

	/// destructor.
	~FWN_MCP_CommandGroup_BlueprintComponent();
};
