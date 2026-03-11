#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Test
//-----------------------------------------------------------------------------

/// Command group for MCPTest commands.
class FWN_MCP_CommandGroup_Test : public FWN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	FWN_MCP_CommandGroup_Test();

	/// destructor.
	~FWN_MCP_CommandGroup_Test() override;

	/// Get command group name.
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @return name.
	FString GetName() const override;

	/// Get application name used as command name prefix.
	FString GetApplicationName() const override;

	/// Called when the commands is registered, allowing it to add its info to the list of available commands.
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @param InOutCommandInfos List of available command infos, which the command can add its info to.
	void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const override;

	/// Execute the command with given parameters and client socket. 
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @param InCommandName command name.
	/// @param InParamsPtr Command parameters, passed as a JSON object.
	/// @param InClientSocketPtr Socket of the client that sent the command, which can be used for sending responses or further communication.
	/// @return JSON object containing the result of command execution, which will be serialized and sent back to the client as a response.
	TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const override;
};