#include "KN_MCP_Module.h"
#include "KN_MCP_ServerThread.h"
#include "KN_MCP_CommandGroup.h"

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
static TArray<TSharedPtr<FKN_MCP_CommandGroup>> CommandGroupPtrs;

/// command group map. key : command name, value : command group.
static TMap<FString, TSharedPtr<FKN_MCP_CommandGroup>> CommandGroupPtrMap;

/// all registered command infos.
static TArray<FKN_MCP_CommandInfo> AllCommandInfos;

//-----------------------------------------------------------------------------
// Defines
//-----------------------------------------------------------------------------

#define MCP_DEFAULT_PORT 27777
#define MCP_MAX_PORT 27787


//-----------------------------------------------------------------------------
// FKN_MCP_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FKN_MCP_Module"

void FKN_MCP_Module::StartupModule()
{
	UE_LOG(LogMCP, Display, TEXT("KN_MCP Module has started"));

	// wait for dependent plugins are initialized.
	PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddLambda([this]()
		{
			StartServer();
		});
}

void FKN_MCP_Module::ShutdownModule()
{
	FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);

	StopServer();

	UE_LOG(LogMCP, Display, TEXT("KN_MCP Module has shut down"));
}

void FKN_MCP_Module::RegisterCommandGroup(TSharedPtr<FKN_MCP_CommandGroup> InGroupPtr)
{
	TArray<FKN_MCP_CommandInfo> commandInfos;
	InGroupPtr->OnRegisterCommands(commandInfos);

	for (const FKN_MCP_CommandInfo& info : commandInfos)
	{
		FString fullName = info.Name;

		TSharedPtr<FKN_MCP_CommandGroup>* addrPrevGroupPtr = CommandGroupPtrMap.Find(fullName);
		if (addrPrevGroupPtr != nullptr)
		{
			UE_LOG(LogMCP, Warning, TEXT("%s command is already registered by %s"), *fullName, *(*addrPrevGroupPtr)->GetName());
			continue;
		}
		CommandGroupPtrMap.Add(fullName, InGroupPtr);
		AllCommandInfos.Add(info);
	}

	CommandGroupPtrs.Add(InGroupPtr);
}

const TArray<FKN_MCP_CommandInfo>& FKN_MCP_Module::GetAllCommandInfos()
{
	return AllCommandInfos;
}

void FKN_MCP_Module::AddUserToolDirectories(const TArray<FString>& InUserToolDirectories)
{
	for (const FString& dir : InUserToolDirectories)
	{
		if (UserToolDirectories.Contains(dir) == false)
		{
			UserToolDirectories.Add(dir);
		}
	}
}

void FKN_MCP_Module::RemoveUserToolDirectories(const TArray<FString>& InUserToolDirectories)
{
	for (const FString& dir : InUserToolDirectories)
	{
		UserToolDirectories.Remove(dir);
	}
}

TSharedPtr<FJsonObject> FKN_MCP_Module::ExecuteCommand(const FString& InCommandName, const FString& InRequestId, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	TSharedPtr<FKN_MCP_CommandGroup>* addrPrevGroupPtr = CommandGroupPtrMap.Find(InCommandName);
	if (addrPrevGroupPtr == nullptr)
	{
		throw std::exception("No Command");
	}
	return (*addrPrevGroupPtr)->Execute(InCommandName, InRequestId, InParamsPtr, InClientSocketPtr);
}

void FKN_MCP_Module::StartServer()
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

	FIPv4Address localAddress;
	FIPv4Address::Parse(TEXT("127.0.0.1"), localAddress);

	// Try each port in range — bind+listen directly to avoid TOCTOU race.
	for (uint16 port = MCP_DEFAULT_PORT; port <= MCP_MAX_PORT; ++port)
	{
		FSocket* rawSocket = socketSubsystem->CreateSocket(NAME_Stream, TEXT("MCP Listening Socket"), false);
		if (rawSocket == nullptr)
		{
			UE_LOG(LogMCP, Warning, TEXT("Failed to create socket for port %d"), port);
			continue;
		}

		rawSocket->SetReuseAddr(false);
		rawSocket->SetNonBlocking(true);

		FIPv4Endpoint endpoint(localAddress, port);

		if (!rawSocket->Bind(*endpoint.ToInternetAddr()))
		{
			UE_LOG(LogMCP, Log, TEXT("Port %d is in use"), port);
			rawSocket->Close();
			socketSubsystem->DestroySocket(rawSocket);
			continue;
		}

		if (!rawSocket->Listen(8))
		{
			UE_LOG(LogMCP, Warning, TEXT("Port %d bind succeeded but listen failed"), port);
			rawSocket->Close();
			socketSubsystem->DestroySocket(rawSocket);
			continue;
		}

		// Success — keep this socket as the listener.
		ListenerSocketPtr = MakeShareable(rawSocket, [](FSocket* Socket)
			{
				// Custom deleter: prevent TSharedPtr from calling delete on FSocket.
				// Socket lifetime is managed by ISocketSubsystem::DestroySocket in StopServer.
			});

		UE_LOG(LogMCP, Display, TEXT("MCP Server listening on %s:%d"), *localAddress.ToString(), port);

		bIsRunning = true;
		ListenerPort = port;

		ServerThread = FRunnableThread::Create(new FKN_MCP_ServerThread(ListenerSocketPtr), TEXT("KN_MCP_ServerThread"));
		if (ServerThread == nullptr)
		{
			UE_LOG(LogMCP, Error, TEXT("Failed to create server thread."));
			StopServer();
		}
		return;
	}

	UE_LOG(LogMCP, Error, TEXT("Failed to find an available port in range %d-%d."), MCP_DEFAULT_PORT, MCP_MAX_PORT);
}

void FKN_MCP_Module::StopServer()
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
		FSocket* rawSocket = ListenerSocketPtr.Get();
		ListenerSocketPtr.Reset();  // Release shared pointer first (custom deleter is no-op).
		rawSocket->Close();
		socketSubsystem->DestroySocket(rawSocket);
	}

	UE_LOG(LogMCP, Log, TEXT("server stopped."));
}

bool FKN_MCP_Module::IsRunningServer() const
{
	return bIsRunning;
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FKN_MCP_Module, KN_MCP)