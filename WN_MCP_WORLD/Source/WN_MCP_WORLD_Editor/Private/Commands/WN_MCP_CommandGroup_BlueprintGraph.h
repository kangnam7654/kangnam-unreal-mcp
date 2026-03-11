#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_BlueprintGraph
//-----------------------------------------------------------------------------

/// Command group for blueprint graph operations (nodes, connections).
class FWN_MCP_CommandGroup_BlueprintGraph : public FWN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Overrides FWN_MCP_CommandGroup
	//-------------------------------------------------------------------------

public:

	/// Get command group name.
	FString GetName() const override;

	/// Get application name used as command name prefix.
	FString GetApplicationName() const override;

	/// Register commands.
	void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const override;

	/// Execute command.
	TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	FWN_MCP_CommandGroup_BlueprintGraph();

	/// destructor.
	~FWN_MCP_CommandGroup_BlueprintGraph();
};
