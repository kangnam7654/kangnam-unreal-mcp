#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"
#include "KN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class FKN_MCP_CommandGroup;
class FSocket;

//-----------------------------------------------------------------------------
// FKN_MCP_Module
//-----------------------------------------------------------------------------

/// module class for KN_MCP plugin.
class FKN_MCP_Module : public IModuleInterface
{
	//-------------------------------------------------------------------------
	// IModuleInterface overrides
	//-------------------------------------------------------------------------

public:

	/// Startup module.
	virtual void StartupModule() override;
	
	/// Shutdown module.
	virtual void ShutdownModule() override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// Get singleton instance of module.
	/// @return module instance.
	static FORCEINLINE FKN_MCP_Module& Get()
	{
		return FModuleManager::LoadModuleChecked<FKN_MCP_Module>("KN_MCP");
	}

	/// Check if module is available.
	/// @return true if module is loaded, false otherwise.
	static FORCEINLINE bool IsAvailable()
	{
		return FModuleManager::Get().IsModuleLoaded("KN_MCP");
	}

	/// Register command group.
	/// @param InGroupPtr command group.
	KN_MCP_API static void RegisterCommandGroup(TSharedPtr<FKN_MCP_CommandGroup> InGroupPtr);

	/// add user tool directories.
	/// @param InUserToolDirectories user tool directories.
	KN_MCP_API void AddUserToolDirectories(const TArray<FString>& InUserToolDirectories);

	/// remove user tool directories.
	/// @param InUserToolDirectories user tool directories.
	KN_MCP_API void RemoveUserToolDirectories(const TArray<FString>& InUserToolDirectories);

	/// get user tool directoreis.
	/// @return user tool directories.
	KN_MCP_API const TArray<FString>& GetUserToolDirectories() const { return UserToolDirectories; }

	/// Get all registered command infos.
	/// @return command infos.
	KN_MCP_API static const TArray<FKN_MCP_CommandInfo>& GetAllCommandInfos();

	/// Execute command.
	/// @param InCommandName command name.
	/// @param InRequestId JSON-RPC 2.0 request id to echo back in response.
	/// @param InParamsPtr command parameters.
	/// @param InClientSocketPtr client socket.
	/// @return result.
	TSharedPtr<FJsonObject> ExecuteCommand(const FString& InCommandName, const FString& InRequestId, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const;

	/// Get the port used by the MCP server.
	/// @return port number.
	KN_MCP_API uint16 GetListenerPort() const { return ListenerPort; }

private:

	/// start server.
	void StartServer();

	/// stop server.
	void StopServer();

public:

	/// is server running?
	/// @return true if server is running, false otherwise.
	KN_MCP_API bool IsRunningServer() const;

	//-------------------------------------------------------------------------
	// Fields
	//-------------------------------------------------------------------------

private:

	/// Delegate handle for OnPostEngineInit callback.
	FDelegateHandle PostEngineInitHandle;

	/// is running client?
	bool bIsRunning = false;

	/// listening port.
	uint16 ListenerPort = 0;

	/// waiting socket for incoming connections.
	TSharedPtr<FSocket> ListenerSocketPtr;

	/// thread for server
	FRunnableThread* ServerThread = nullptr;

	/// user tool directories.
	TArray<FString> UserToolDirectories;
};

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DECLARE_LOG_CATEGORY_EXTERN(LogMCP, Log, All);