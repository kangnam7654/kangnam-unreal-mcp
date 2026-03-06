#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class FWN_MCP_CommandGroup;
class FSocket;

//-----------------------------------------------------------------------------
// FWN_MCP_Module
//-----------------------------------------------------------------------------

/// module class for WN_MCP plugin.
class FWN_MCP_Module : public IModuleInterface
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
	static FORCEINLINE FWN_MCP_Module& Get()
	{
		return FModuleManager::LoadModuleChecked<FWN_MCP_Module>("WN_MCP");
	}

	/// Check if module is available.
	/// @return true if module is loaded, false otherwise.
	static FORCEINLINE bool IsAvailable()
	{
		return FModuleManager::Get().IsModuleLoaded("WN_MCP");
	}

	/// Register command group.
	/// @param InGroupPtr command group.
	WN_MCP_API static void RegisterCommandGroup(TSharedPtr<FWN_MCP_CommandGroup> InGroupPtr);

	/// add user tool directories.
	/// @param InUserToolDirectories user tool directories.
	WN_MCP_API void AddUserToolDirectories(const TArray<FString>& InUserToolDirectories);

	/// remove user tool directories.
	/// @param InUserToolDirectories user tool directories.
	WN_MCP_API void RemoveUserToolDirectories(const TArray<FString>& InUserToolDirectories);

	/// get user tool directoreis.
	/// @return user tool directories.
	WN_MCP_API const TArray<FString>& GetUserToolDirectories() const { return UserToolDirectories; }

	/// Execute command.
	/// @param InCommandName command name.
	/// @param InParamsPtr command parameters.
	/// @param InClientSocketPtr client socket.
	/// @return result.
	TSharedPtr<FJsonObject> ExecuteCommand(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const;

	/// Get the port used by the MCP server.
	/// @return port number.
	WN_MCP_API uint16 GetListenerPort() const { return ListenerPort; }

private:

	/// start server.
	void StartServer();

	/// stop server.
	void StopServer();

public:

	/// is server running?
	/// @return true if server is running, false otherwise.
	WN_MCP_API bool IsRunningServer() const;

	//-------------------------------------------------------------------------
	// Fields
	//-------------------------------------------------------------------------

private:

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