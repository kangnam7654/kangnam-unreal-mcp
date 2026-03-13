#pragma once

#include "HAL/Runnable.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include <atomic>

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class FSocket;
class FJsonObject;

//-----------------------------------------------------------------------------
// FKN_MCP_ServerThread
//-----------------------------------------------------------------------------

/// Runnable class for MCP Client to handle incoming connections and messages.
class FKN_MCP_ServerThread : public FRunnable
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
	FKN_MCP_ServerThread(TSharedPtr<FSocket> InListenerSocketPtr);

	/// Destructor.
	virtual ~FKN_MCP_ServerThread();

private:

	/// execute command from client on the game thread with timeout.
	/// @param InCommandName command type string to identify the command.
	/// @param InRequestId JSON-RPC 2.0 request id to echo back in response.
	/// @param InParamsPtr parameters for the command, passed as a JSON object.
	/// @param InClientSocketPtr client socket for the current connection.
	/// @return command execution result as a string, which will be sent back to the client as a response.
	FString ExecuteCommand(const FString& InCommandName, const FString& InRequestId, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr);

	//-------------------------------------------------------------------------
	// Fields.
	//-------------------------------------------------------------------------

private:

	/// is running?
	std::atomic<bool> bIsRunning{false};

	/// Shared pointer to the listening socket for accepting incoming connections.
	TSharedPtr<FSocket> ListenerSocketPtr;

	/// Timeout in seconds for game thread command execution.
	static constexpr float CommandTimeoutSeconds = 60.0f;
};