#include "WN_MCP_ServerThread.h"
#include "WN_MCP_Module.h"

#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Serialization/JsonSerializer.h"

//-----------------------------------------------------------------------------
// Statics
//------------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_ServerThread
//-----------------------------------------------------------------------------

bool FWN_MCP_ServerThread::Init()
{
	bIsRunning = true;
	return true;
}

uint32 FWN_MCP_ServerThread::Run()
{
	ISocketSubsystem* socketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);

	uint8 buffer[8192]; // 8 KiB.

	// wait for the server to start and bind the listening socket.
	while (bIsRunning)
	{
		bool isPending = false;
		ListenerSocketPtr->HasPendingConnection(isPending);
		if (isPending == false)
		{
			FPlatformProcess::Sleep(0.01f);
			continue;
		}

		UE_LOG(LogMCP, Log, TEXT("Incoming connection detected."));
		ClientSocketPtr = MakeShareable(ListenerSocketPtr->Accept(TEXT("WN_MCP_Server")));
		if (ClientSocketPtr.IsValid() == false)
		{
			UE_LOG(LogMCP, Error, TEXT("Failed to accept incoming connection."));
			return 1;
		}

		ClientSocketPtr->SetNoDelay(true);
		int32 bufferSize = 65536; // 64KiB
		ClientSocketPtr->SetSendBufferSize(bufferSize, bufferSize);
		ClientSocketPtr->SetReceiveBufferSize(bufferSize, bufferSize);

		// main loop for receiving messages from the client.
		while (bIsRunning)
		{
			int32 bytesRead = 0;
			// receive data from the client.
			if (ClientSocketPtr->Recv(buffer, sizeof(buffer), bytesRead))
			{
				if (bytesRead > 0)
				{
					buffer[bytesRead] = 0; // null-terminate the buffer.

					const FString message = UTF8_TO_TCHAR(buffer);

					TSharedPtr<FJsonObject> jsonObject;
					TSharedRef<TJsonReader<>> jsonReader = TJsonReaderFactory<>::Create(message);
					if (FJsonSerializer::Deserialize(jsonReader, jsonObject) && jsonObject.IsValid())
					{
						FString commandName;
						if (jsonObject->TryGetStringField(TEXT("id"), commandName))
						{
							// execute command.
							FString response = ExecuteCommand(commandName, jsonObject->GetObjectField(TEXT("params")));
							UE_LOG(LogMCP, Log, TEXT("Executed command '%s' with response: %s"), *commandName, *response);

							// send response back to client.
							int32 bytesSend;
							if (ClientSocketPtr->Send((uint8*)TCHAR_TO_UTF8(*response), response.Len(), bytesSend))
							{
								UE_LOG(LogMCP, Log, TEXT("Sent response to client for command '%s': %s"), *commandName, *response);
							}
							else
							{
								UE_LOG(LogMCP, Warning, TEXT("Failed to send response to client for command '%s'"), *commandName);
							}
						}
						else
						{
							UE_LOG(LogMCP, Warning, TEXT("Received JSON message without 'type' field: %s"), *message);
						}
					}
					else
					{
						UE_LOG(LogMCP, Warning, TEXT("Received invalid JSON message: %s"), *message);
					}
				}
			}
			else
			{
				const ESocketErrors lastError = socketSubsystem->GetLastErrorCode();
				// no data available, sleep and retry.
				if (lastError == SE_EWOULDBLOCK)
				{
					FPlatformProcess::Sleep(0.01f);
					continue;
				}
				// transient error, sleep and retry.
				else if (lastError == SE_EINPROGRESS || lastError == SE_EINTR)
				{
					FPlatformProcess::Sleep(0.01f);
					continue;
				}
				// unexpected error, log and break the loop to close the connection.
				else
				{
					UE_LOG(LogMCP, Error, TEXT("Error receiving data from client: %s"), socketSubsystem->GetSocketError(lastError));

					if (ClientSocketPtr.IsValid())
					{
						ClientSocketPtr->Close();
						ClientSocketPtr.Reset();
					}

					break; // break message loop and wait new connection.
				}
			}
		}
	}

	return 0;
}

void FWN_MCP_ServerThread::Stop()
{
	bIsRunning = false;
}

void FWN_MCP_ServerThread::Exit()
{
}

FWN_MCP_ServerThread::FWN_MCP_ServerThread(TSharedPtr<FSocket> InListenerSocketPtr)
	: ListenerSocketPtr(InListenerSocketPtr)
{
}

FWN_MCP_ServerThread::~FWN_MCP_ServerThread()
{
}


FString FWN_MCP_ServerThread::ExecuteCommand(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr)
{
	TPromise<FString> promise;
	TFuture<FString> future = promise.GetFuture();

	// ensure command execution happens on the game thread, since many Unreal APIs are not thread-safe and must be called from the game thread.
	AsyncTask(ENamedThreads::GameThread, [this, InCommandName, InParamsPtr, InClientSocketPtr = ClientSocketPtr, InPromise = MoveTemp(promise)]() mutable
		{
			TSharedPtr<FJsonObject> jsonResponse = MakeShareable(new FJsonObject);
			try
			{
				jsonResponse = FWN_MCP_Module::Get().ExecuteCommand(InCommandName, InParamsPtr, InClientSocketPtr);
			}
			catch (const std::exception& InException)
			{
				jsonResponse->SetStringField(TEXT("status"), TEXT("error"));
				jsonResponse->SetStringField(TEXT("error"), UTF8_TO_TCHAR(InException.what()));
			}

			FString result;
			TSharedRef<TJsonWriter<>> jsonWriter = TJsonWriterFactory<>::Create(&result);
			FJsonSerializer::Serialize(jsonResponse.ToSharedRef(), jsonWriter);
			InPromise.SetValue(result);
		});

	// wait for the command execution to complete and get the result.
	return future.Get();
}