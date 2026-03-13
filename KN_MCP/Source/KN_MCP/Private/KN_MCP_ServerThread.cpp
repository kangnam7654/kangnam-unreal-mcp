#include "KN_MCP_ServerThread.h"
#include "KN_MCP_Module.h"

#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Serialization/JsonSerializer.h"

//-----------------------------------------------------------------------------
// Statics
//------------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FKN_MCP_ServerThread
//-----------------------------------------------------------------------------

bool FKN_MCP_ServerThread::Init()
{
	bIsRunning = true;
	return true;
}

uint32 FKN_MCP_ServerThread::Run()
{
	ISocketSubsystem* socketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);

	uint8 buffer[8193]; // 8 KiB + 1 byte for null-terminator.

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

		// Use local variable instead of member to avoid cross-thread shared pointer races.
		TSharedPtr<FSocket> clientSocketPtr = MakeShareable(ListenerSocketPtr->Accept(TEXT("KN_MCP_Server")));
		if (clientSocketPtr.IsValid() == false)
		{
			UE_LOG(LogMCP, Error, TEXT("Failed to accept incoming connection."));
			return 1;
		}

		clientSocketPtr->SetNoDelay(true);
		int32 bufferSize = 65536; // 64KiB
		clientSocketPtr->SetSendBufferSize(bufferSize, bufferSize);
		clientSocketPtr->SetReceiveBufferSize(bufferSize, bufferSize);

		// main loop for receiving messages from the client.
		while (bIsRunning)
		{
			int32 bytesRead = 0;
			// receive data from the client.
			if (clientSocketPtr->Recv(buffer, sizeof(buffer) - 1, bytesRead))
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
						if (jsonObject->TryGetStringField(TEXT("method"), commandName))
						{
							// extract request id for JSON-RPC 2.0 response correlation.
							FString requestId;
							jsonObject->TryGetStringField(TEXT("id"), requestId);

							// extract params safely (may be absent or null).
							TSharedPtr<FJsonObject> paramsPtr;
							if (!jsonObject->TryGetObjectField(TEXT("params"), paramsPtr) || !paramsPtr.IsValid())
							{
								paramsPtr = MakeShareable(new FJsonObject);
							}

							// execute command.
							FString response = ExecuteCommand(commandName, requestId, paramsPtr, clientSocketPtr);
							UE_LOG(LogMCP, Log, TEXT("Executed command '%s' with response: %s"), *commandName, *response);

							// Send response back to client (UTF-8 byte count, not TCHAR character count)
							FTCHARToUTF8 utf8Response(*response);
							int32 bytesSent = 0;
							const int32 totalBytes = utf8Response.Length();
							const uint8* dataPtr = (const uint8*)utf8Response.Get();
							int32 offset = 0;

							while (offset < totalBytes)
							{
								int32 sent = 0;
								if (clientSocketPtr->Send(dataPtr + offset, totalBytes - offset, sent))
								{
									offset += sent;
								}
								else
								{
									UE_LOG(LogMCP, Warning, TEXT("Failed to send response to client for command '%s' (sent %d/%d bytes)"), *commandName, offset, totalBytes);
									break;
								}
							}

							if (offset == totalBytes)
							{
								UE_LOG(LogMCP, Log, TEXT("Sent response to client for command '%s' (%d bytes)"), *commandName, totalBytes);
							}
						}
						else
						{
							UE_LOG(LogMCP, Warning, TEXT("Received JSON message without 'method' field: %s"), *message);
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

					if (clientSocketPtr.IsValid())
					{
						clientSocketPtr->Close();
						clientSocketPtr.Reset();
					}

					break; // break message loop and wait new connection.
				}
			}
		}
	}

	return 0;
}

void FKN_MCP_ServerThread::Stop()
{
	bIsRunning = false;
}

void FKN_MCP_ServerThread::Exit()
{
}

FKN_MCP_ServerThread::FKN_MCP_ServerThread(TSharedPtr<FSocket> InListenerSocketPtr)
	: ListenerSocketPtr(InListenerSocketPtr)
{
}

FKN_MCP_ServerThread::~FKN_MCP_ServerThread()
{
}


FString FKN_MCP_ServerThread::ExecuteCommand(const FString& InCommandName, const FString& InRequestId, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr)
{
	TPromise<FString> promise;
	TFuture<FString> future = promise.GetFuture();

	// ensure command execution happens on the game thread, since many Unreal APIs are not thread-safe and must be called from the game thread.
	AsyncTask(ENamedThreads::GameThread, [InCommandName, InRequestId, InParamsPtr, InClientSocketPtr, InPromise = MoveTemp(promise)]() mutable
		{
			TSharedPtr<FJsonObject> jsonResponse = MakeShareable(new FJsonObject);
			try
			{
				jsonResponse = FKN_MCP_Module::Get().ExecuteCommand(InCommandName, InRequestId, InParamsPtr, InClientSocketPtr);
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

	// wait for the command execution with timeout to prevent infinite blocking.
	const FTimespan timeout = FTimespan::FromSeconds(CommandTimeoutSeconds);
	if (future.WaitFor(timeout))
	{
		return future.Get();
	}

	// Timeout — return error response.
	UE_LOG(LogMCP, Error, TEXT("Command '%s' timed out after %.0f seconds"), *InCommandName, CommandTimeoutSeconds);

	TSharedPtr<FJsonObject> errorResponse = MakeShareable(new FJsonObject);
	errorResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);
	errorObj->SetNumberField(TEXT("code"), -32001);
	errorObj->SetStringField(TEXT("message"), TEXT("Command execution timed out"));
	errorObj->SetStringField(TEXT("data"), FString::Printf(TEXT("Command '%s' did not complete within %.0f seconds"), *InCommandName, CommandTimeoutSeconds));
	errorResponse->SetObjectField(TEXT("error"), errorObj);
	errorResponse->SetStringField(TEXT("id"), InRequestId);

	FString result;
	TSharedRef<TJsonWriter<>> jsonWriter = TJsonWriterFactory<>::Create(&result);
	FJsonSerializer::Serialize(errorResponse.ToSharedRef(), jsonWriter);
	return result;
}