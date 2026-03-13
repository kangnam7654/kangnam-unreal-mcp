#pragma once

#include "KN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class AActor;

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_ActorComponent
//-----------------------------------------------------------------------------

/// Command group for runtime Actor component operations (add/remove/read).
class FKN_MCP_CommandGroup_ActorComponent : public FKN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Overrides FKN_MCP_CommandGroup
	//-------------------------------------------------------------------------

public:

	/// Get command group name.
	FString GetName() const override;

	/// Get application name used as command name prefix.
	FString GetApplicationName() const override;

	/// Register commands.
	void OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const override;

	/// Execute command.
	TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	FKN_MCP_CommandGroup_ActorComponent();

	/// destructor.
	~FKN_MCP_CommandGroup_ActorComponent();
};
