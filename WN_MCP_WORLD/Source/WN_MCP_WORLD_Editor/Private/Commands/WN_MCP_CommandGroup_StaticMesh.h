#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_StaticMesh
//-----------------------------------------------------------------------------

/// Command group for static mesh asset query operations.
class FWN_MCP_CommandGroup_StaticMesh : public FWN_MCP_CommandGroup
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
	FWN_MCP_CommandGroup_StaticMesh();

	/// destructor.
	~FWN_MCP_CommandGroup_StaticMesh();
};
