#include "WN_MCP_Module.h"
#include "WN_MCP_ServerThread.h"
#include "WN_MCP_CommandGroup.h"

#include "Modules/ModuleManager.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCP);

//-----------------------------------------------------------------------------
// Statics
//-----------------------------------------------------------------------------

/// command group array.
static TArray<TSharedPtr<FWN_MCP_CommandGroup>> CommandGroupPtrs;

/// command group map. key : command name, value : command group.
static TMap<FString, TSharedPtr<FWN_MCP_CommandGroup>> CommandGroupPtrMap;

//-----------------------------------------------------------------------------
// Defines
//-----------------------------------------------------------------------------

#define MCP_DEFAULT_PORT 27777
#define MCP_MAX_PORT 27787

//-----------------------------------------------------------------------------
// Helper Functions
//-----------------------------------------------------------------------------

/// Find an available port within the specified range
/// @param InStartPort Starting port number
/// @param InEndPort Ending port number (inclusive)
/// @param OutAvailablePort Output parameter for the available port
/// @return true if an available port was found, false otherwise
static bool WN_FindAvailablePort(uint16 InStartPort, uint16 InEndPort, uint16& OutAvailablePort)
{
	ISocketSubsystem* socketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (socketSubsystem == nullptr)
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to get socket subsystem in WN_FindAvailablePort"));
		return false;
	}

	for (uint16 port = InStartPort; port <= InEndPort; ++port)
	{
		FIPv4Address localAddress;
		FIPv4Address::Parse(TEXT("127.0.0.1"), localAddress);
		FIPv4Endpoint endpoint(localAddress, port);

		// Create a temporary test socket to check if the port is available
		FSocket* testSocket = socketSubsystem->CreateSocket(NAME_Stream, TEXT("MCP Test Socket"), false);
		if (testSocket == nullptr)
		{
			UE_LOG(LogMCP, Warning, TEXT("Failed to create test socket for port %d"), port);
			continue;
		}

		testSocket->SetReuseAddr(false);  // Changed to false for exclusive access
		testSocket->SetNonBlocking(false);

		// Try to bind to the port
		bool bPortAvailable = false;
		if (testSocket->Bind(*endpoint.ToInternetAddr()))
		{
			// Bind succeeded, now verify by trying to listen
			if (testSocket->Listen(1))
			{
				bPortAvailable = true;
				UE_LOG(LogMCP, Log, TEXT("Port %d is available"), port);
			}
			else
			{
				UE_LOG(LogMCP, Warning, TEXT("Port %d bind succeeded but listen failed"), port);
			}
		}
		else
		{
			ESocketErrors lastError = socketSubsystem->GetLastErrorCode();
			UE_LOG(LogMCP, Log, TEXT("Port %d is in use (bind failed with error code: %d)"), port, (int32)lastError);
		}
		
		testSocket->Close();
		socketSubsystem->DestroySocket(testSocket);

		if (bPortAvailable)
		{
			OutAvailablePort = port;
			UE_LOG(LogMCP, Display, TEXT("Found available port: %d"), port);
			return true;
		}
	}

	UE_LOG(LogMCP, Error, TEXT("No available ports found in range %d-%d"), InStartPort, InEndPort);
	return false;
}

//-----------------------------------------------------------------------------
// FWN_MCP_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FWN_MCP_Module"

void FWN_MCP_Module::StartupModule()
{
	UE_LOG(LogMCP, Display, TEXT("Kangnam Kim MCP Module has started"));

	// wait for dependent plugins are initialized.
	FCoreDelegates::OnPostEngineInit.AddLambda([this]()
		{
			StartServer();
		});
}

void FWN_MCP_Module::ShutdownModule()
{
	StopServer();

	UE_LOG(LogMCP, Display, TEXT("Kangnam Kim MCP Module has shut down"));
}

void FWN_MCP_Module::RegisterCommandGroup(TSharedPtr<FWN_MCP_CommandGroup> InGroupPtr)
{
	TArray<FString> commandNames;
	InGroupPtr->OnRegisterCommands(commandNames);
	for (const FString& name : commandNames)
	{
		TSharedPtr<FWN_MCP_CommandGroup>* addrPrevGroupPtr = CommandGroupPtrMap.Find(name);
		if (addrPrevGroupPtr != nullptr)
		{
			UE_LOG(LogMCP, Warning, TEXT("%s command is already registered by %s"), *name, *(*addrPrevGroupPtr)->GetName());
			continue;
		}
		CommandGroupPtrMap.Add(name, InGroupPtr);
	}

	CommandGroupPtrs.Add(InGroupPtr);
}

void FWN_MCP_Module::AddUserToolDirectories(const TArray<FString>& InUserToolDirectories)
{
	for (const FString& dir : InUserToolDirectories)
	{
		if (UserToolDirectories.Contains(dir) == false)
		{
			UserToolDirectories.Add(dir);
		}
	}
}

void FWN_MCP_Module::RemoveUserToolDirectories(const TArray<FString>& InUserToolDirectories)
{
	for (const FString& dir : InUserToolDirectories)
	{
		UserToolDirectories.Remove(dir);
	}
}

TSharedPtr<FJsonObject> FWN_MCP_Module::ExecuteCommand(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	TSharedPtr<FWN_MCP_CommandGroup>* addrPrevGroupPtr = CommandGroupPtrMap.Find(InCommandName);
	if (addrPrevGroupPtr == nullptr)
	{
		throw std::exception("No Command");
	}
	return (*addrPrevGroupPtr)->Execute(InCommandName, InParamsPtr, InClientSocketPtr);
}

void FWN_MCP_Module::StartServer()
{
	if (bIsRunning)
	{
		UE_LOG(LogMCP, Warning, TEXT("Server is already running."));
		return;
	}

	ISocketSubsystem* socketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (socketSubsystem == nullptr)
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to get socket subsystem."));
		return;
	}

	uint16 availablePort = MCP_DEFAULT_PORT;
	if (!WN_FindAvailablePort(MCP_DEFAULT_PORT, MCP_MAX_PORT, availablePort))
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to find an available port in range %d-%d."), MCP_DEFAULT_PORT, MCP_MAX_PORT);
		return;
	}

	ListenerSocketPtr = TSharedPtr<FSocket>(socketSubsystem->CreateSocket(NAME_Stream, TEXT("MCP Listening Socket"), false));
	if (ListenerSocketPtr.IsValid() == false)
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to create listener socket."));
		return;
	}

	ListenerSocketPtr->SetReuseAddr(false);  // Use exclusive access on Windows
	ListenerSocketPtr->SetNonBlocking(true);

	FIPv4Address localAddress;
	FIPv4Address::Parse(TEXT("127.0.0.1"), localAddress);
	FIPv4Endpoint endpoint(localAddress, availablePort);
	
	if (!ListenerSocketPtr->Bind(*endpoint.ToInternetAddr()))
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to bind listener socket to %s:%d."), *localAddress.ToString(), availablePort);
		return;
	}

	if (!ListenerSocketPtr->Listen(8))
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to start listener on socket."));
		return;
	}

	UE_LOG(LogMCP, Display, TEXT("MCP Server listening on %s:%d"), *localAddress.ToString(), availablePort);

	bIsRunning = true;
	ListenerPort = availablePort;

	ServerThread = FRunnableThread::Create(new FWN_MCP_ServerThread(ListenerSocketPtr), TEXT("WN_MCP_ServerThread"));
	if (ServerThread == nullptr)
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to create server thread."));
		StopServer();
		return;
	}
}

void FWN_MCP_Module::StopServer()
{
	UE_LOG(LogMCP, Log, TEXT("Stopping server."));

	if (bIsRunning == false)
	{
		return;
	}

	bIsRunning = false;

	if (ServerThread != nullptr)
	{
		ServerThread->Kill(true);
		delete ServerThread;
		ServerThread = nullptr;
	}

	// get socket subsystem.
	ISocketSubsystem* socketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (socketSubsystem == nullptr)
	{
		UE_LOG(LogMCP, Error, TEXT("Failed to get socket subsystem."));
		return;
	}

	// destroy listener socket.
	if (ListenerSocketPtr.IsValid())
	{
		ListenerSocketPtr->Close();
		socketSubsystem->DestroySocket(ListenerSocketPtr.Get());
		ListenerSocketPtr.Reset();
	}

	UE_LOG(LogMCP, Log, TEXT("server stopped."));
}

bool FWN_MCP_Module::IsRunningServer() const
{
	return bIsRunning;
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FWN_MCP_Module, WN_MCP)