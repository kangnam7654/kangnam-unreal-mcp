#pragma once

#include "HAL/Runnable.h"
#include "Interfaces/IPv4/IPv4Address.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class FSocket;
class FJsonObject;
class UWN_MCP_Subsystem;

//-----------------------------------------------------------------------------
// FWN_MCP_ServerThread
//-----------------------------------------------------------------------------

/// Runnable class for MCP Client to handle incoming connections and messages.
class FWN_MCP_ServerThread : public FRunnable
{
	//-------------------------------------------------------------------------
	// FRunnable overrides
	//-------------------------------------------------------------------------

public:

	/// Initializes the runnable object.
	/// 
	/// This method is called in the context of the thread object that aggregates this, not the
	/// thread that passes this runnable to a new thread.
	/// 
	/// @return True if initialization was successful, false otherwise
	/// @see Run, Stop, Exit
	virtual bool Init() override;

	/// Runs the runnable object.
	/// 
	/// This is where all per object thread work is done. This is only called if the initialization was successful.
	/// 
	/// @return The exit code of the runnable object
	/// @see Init, Stop, Exit
	virtual uint32 Run() override;

	/// Stops the runnable object.
	/// 
	/// This is called if a thread is requested to terminate early.
	/// @see Init, Run, Exit
	virtual void Stop() override;

	/// Exits the runnable object.
	/// 
	/// Called in the context of the aggregating thread to perform any cleanup.
	/// @see Init, Run, Stop
	virtual void Exit() override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// Constructor.
	/// @param InListenerSocketPtr Shared pointer to the listening socket for accepting incoming connections.
	FWN_MCP_ServerThread(TSharedPtr<FSocket> InListenerSocketPtr);

	/// Destructor.
	virtual ~FWN_MCP_ServerThread();

private:

	/// execute command from client.
	/// @param InCommandName command type string to identify the command.
	/// @param InParamsPtr parameters for the command, passed as a JSON object.
	/// @return command execution result as a string, which will be sent back to the client as a response.
	FString ExecuteCommand(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr);

	//-------------------------------------------------------------------------
	// Fields.
	//-------------------------------------------------------------------------

private:

	/// is running?
	bool bIsRunning = false;

	/// Pointer to the MCP subsystem instance.
	UWN_MCP_Subsystem* Subsystem;

	/// Shared pointer to the listening socket for accepting incoming connections.
	TSharedPtr<FSocket> ListenerSocketPtr;

	/// Shared pointer to the client socket for receiving messages from the client.
	TSharedPtr<FSocket> ClientSocketPtr;
};