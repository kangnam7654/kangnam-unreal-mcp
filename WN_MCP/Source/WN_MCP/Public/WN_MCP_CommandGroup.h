#pragma once

#include "CoreMinimal.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class FSocket;
class FJsonObject;

//-----------------------------------------------------------------------------
// FWN_MCP_CommandInfo
//-----------------------------------------------------------------------------

/// Command registration info.
struct FWN_MCP_CommandInfo
{
	FString Name;
	FString Description;
	bool bIsSimple;
};

//-----------------------------------------------------------------------------
// Defines
//-----------------------------------------------------------------------------

/*
	JSON-RPC 2.0 Success Response Format:
	{
		"jsonrpc": "2.0",
		"result": {
			"key1": "value1",
			"key2": "value2",
			...
		},
		"id": "request_id"
	}

	JSON-RPC 2.0 Error Response Format:
	{
		"jsonrpc": "2.0",
		"error": {
			"code": -32600,
			"message": "Invalid Request",
			"data": "additional error information"
		},
		"id": "request_id"
	}

	Error Code Standards:
	- code: must be an integer
	- message: must be a string providing a short description of the error
	- data: may contain a primitive or structured value that contains additional information about the error (optional)
*/

/// Register MCP command group.
#define WN_MCP_REGISTER_COMMAND_GROUP(CommandGroupClass) class RegisterCommandGroup_ ##CommandGroupClass\
{\
public:\
	RegisterCommandGroup_ ##CommandGroupClass()\
	{\
		TSharedPtr<CommandGroupClass> commandGroupPtr = MakeShared<CommandGroupClass>();\
		FWN_MCP_Module::RegisterCommandGroup(commandGroupPtr);\
	}\
};\
static RegisterCommandGroup_ ##CommandGroupClass RegisterCommandGroupInstance_ ##CommandGroupClass

/// Register a command (requires custom Python Tool).
/// GetName() prefix is prepended automatically (e.g. "Actor" + "_" + "spawn_actor" = "Actor_spawn_actor").
#define WN_MCP_REGISTER_COMMAND(InOutList, CommandName, CommandDesc) \
	InOutList.Add({ GetName() + TEXT("_") + FString(TEXT(CommandName)), FString(TEXT(CommandDesc)), false })

/// Register a simple command (Python Tool auto-generated).
/// GetName() prefix is prepended automatically (e.g. "Actor" + "_" + "spawn_actor" = "Actor_spawn_actor").
#define WN_MCP_REGISTER_SIMPLE_COMMAND(InOutList, CommandName, CommandDesc) \
	InOutList.Add({ GetName() + TEXT("_") + FString(TEXT(CommandName)), FString(TEXT(CommandDesc)), true })

/// Parse error - Invalid JSON was received by the server.
#define WN_JSON_RPC_ERROR_PARSE_ERROR -32700

/// Invalid Request - The JSON sent is not a valid Request object.
#define WN_JSON_RPC_ERROR_INVALID_REQUEST -32600

/// Method not found - The method does not exist / is not available.
#define WN_JSON_RPC_ERROR_METHOD_NOT_FOUND -32601

/// Invalid params - Invalid method parameter(s).
#define WN_JSON_RPC_ERROR_INVALID_PARAMS -32602

/// Internal error - Internal JSON-RPC error.
#define WN_JSON_RPC_ERROR_INTERNAL_ERROR -32603

/// Server error - Reserved for implementation-defined server errors (-32768 to -32000).
#define WN_JSON_RPC_ERROR_SERVER_ERROR -32000

/// Custom error - Command execution failed.
#define WN_JSON_RPC_ERROR_COMMAND_FAILED -32001

/// Custom error - Invalid command arguments.
#define WN_JSON_RPC_ERROR_INVALID_ARGUMENTS -32002

/// Custom error - Unreal Engine communication error.
#define WN_JSON_RPC_ERROR_UE_COMMUNICATION_ERROR -32003

/// Get error message for JSON-RPC 2.0 error code.
#define WN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode) \
	(InErrorCode == WN_JSON_RPC_ERROR_PARSE_ERROR ? TEXT("Parse error") : \
	 InErrorCode == WN_JSON_RPC_ERROR_INVALID_REQUEST ? TEXT("Invalid Request") : \
	 InErrorCode == WN_JSON_RPC_ERROR_METHOD_NOT_FOUND ? TEXT("Method not found") : \
	 InErrorCode == WN_JSON_RPC_ERROR_INVALID_PARAMS ? TEXT("Invalid params") : \
	 InErrorCode == WN_JSON_RPC_ERROR_INTERNAL_ERROR ? TEXT("Internal error") : \
	 InErrorCode == WN_JSON_RPC_ERROR_SERVER_ERROR ? TEXT("Server error") : \
	 InErrorCode == WN_JSON_RPC_ERROR_COMMAND_FAILED ? TEXT("Command execution failed") : \
	 InErrorCode == WN_JSON_RPC_ERROR_INVALID_ARGUMENTS ? TEXT("Invalid command arguments") : \
	 InErrorCode == WN_JSON_RPC_ERROR_UE_COMMUNICATION_ERROR ? TEXT("Unreal Engine communication error") : \
	 TEXT("Unknown error"))

/// Return command response with given result following JSON-RPC 2.0 success format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the response.
/// The 'result' field contains the command execution result.
/// 
/// Usage: WN_RETURN_COMMAND_RESPONSE(InResultPtr);
/// 
/// Returns JSON-RPC 2.0 success response format:
/// {
///   "jsonrpc": "2.0",
///   "result": {
///     "key1": "value1",
///     "key2": "value2"
///   },
///   "id": "command_name"
/// }
/// 
/// @param InJsonResultObjectPtr The result data to include in the 'result' field (TSharedPtr<FJsonObject>)
#define WN_RETURN_COMMAND_RESPONSE(InJsonResultObjectPtr) \
	TSharedPtr<FJsonObject> jsonResponse = MakeShareable(new FJsonObject);\
	jsonResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	if (InResultPtr.IsValid())\
	{\
		jsonResponse->SetObjectField(TEXT("result"), InJsonResultObjectPtr);\
	}\
	else\
	{\
		jsonResponse->SetObjectField(TEXT("result"), MakeShareable(new FJsonObject));\
	}\
	jsonResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonResponse

/// Return command response with given array result following JSON-RPC 2.0 success format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the response.
/// The 'result' field contains an array of values.
/// 
/// Usage: WN_RETURN_COMMAND_ARRAY_RESPONSE(jsonArrayValues);
/// 
/// Returns JSON-RPC 2.0 success response format:
/// {
///   "jsonrpc": "2.0",
///   "result": [
///     "value1",
///     "value2",
///     ...
///   ],
///   "id": "command_name"
/// }
/// 
/// @param InJsonResultValuePtrArray The array values to include in the 'result' field (TArray<TSharedPtr<FJsonValue>>)
#define WN_RETURN_COMMAND_ARRAY_RESPONSE(InJsonResultValuePtrArray) \
	TSharedPtr<FJsonObject> jsonResponse = MakeShareable(new FJsonObject);\
	jsonResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	jsonResponse->SetArrayField(TEXT("result"), InJsonResultValuePtrArray);\
	jsonResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonResponse

/// Return command response with given text result following JSON-RPC 2.0 success format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the response.
/// The 'result' field contains a text string with the command execution result.
/// 
/// Usage: WN_RETURN_COMMAND_TEXT_RESPONSE(TEXT("Command executed successfully"));
/// 
/// Returns JSON-RPC 2.0 success response format:
/// {
///   "jsonrpc": "2.0",
///   "result": "Command executed successfully",
///   "id": "command_name"
/// }
/// 
/// @param InResultMessage The result message to include in the 'result' field (const TCHAR*)
#define WN_RETURN_COMMAND_TEXT_RESPONSE(InResultMessage) \
	TSharedPtr<FJsonObject> jsonResponse = MakeShareable(new FJsonObject);\
	jsonResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	jsonResponse->SetStringField(TEXT("result"), InResultMessage);\
	jsonResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonResponse

/// Return command response with given error code and object data following JSON-RPC 2.0 error format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the error.
/// The 'data' field contains a JSON object with error details.
/// 
/// Usage: WN_RETURN_COMMAND_ERROR_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, InErrorDataObjectPtr);
/// 
/// Returns JSON-RPC 2.0 error response format:
/// {
///   "jsonrpc": "2.0",
///   "error": {
///     "code": -32602,
///     "message": "Invalid params",
///     "data": { "key1": "value1", ... }
///   },
///   "id": "command_name"
/// }
/// 
/// @param InErrorCode The JSON-RPC 2.0 error code
/// @param InErrorDataObjectPtr The error data object to include in 'data' field (TSharedPtr<FJsonObject>)
#define WN_RETURN_COMMAND_ERROR_RESPONSE(InErrorCode, InErrorDataObjectPtr) \
	TSharedPtr<FJsonObject> jsonErrorResponse = MakeShareable(new FJsonObject);\
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);\
	errorObj->SetNumberField(TEXT("code"), InErrorCode);\
	errorObj->SetStringField(TEXT("message"), WN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode));\
	if (InErrorDataObjectPtr.IsValid())\
	{\
		errorObj->SetObjectField(TEXT("data"), InErrorDataObjectPtr);\
	}\
	jsonErrorResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	jsonErrorResponse->SetObjectField(TEXT("error"), errorObj);\
	jsonErrorResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonErrorResponse

/// Return command response with given error code and text message following JSON-RPC 2.0 error format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the error.
/// The 'data' field contains a text string with error details.
/// 
/// Usage: WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing 'message' parameter"));
/// 
/// Returns JSON-RPC 2.0 error response format:
/// {
///   "jsonrpc": "2.0",
///   "error": {
///     "code": -32602,
///     "message": "Invalid params",
///     "data": "Missing 'message' parameter"
///   },
///   "id": "command_name"
/// }
/// 
/// @param InErrorCode The JSON-RPC 2.0 error code
/// @param InErrorMessage The error message to include in 'data' field (const TCHAR*)
#define WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(InErrorCode, InErrorMessage) \
	TSharedPtr<FJsonObject> jsonErrorResponse = MakeShareable(new FJsonObject);\
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);\
	errorObj->SetNumberField(TEXT("code"), InErrorCode);\
	errorObj->SetStringField(TEXT("message"), WN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode));\
	errorObj->SetStringField(TEXT("data"), InErrorMessage);\
	jsonErrorResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	jsonErrorResponse->SetObjectField(TEXT("error"), errorObj);\
	jsonErrorResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonErrorResponse

/// Return command response with given error code and array data following JSON-RPC 2.0 error format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the error.
/// The 'data' field contains an array of error messages.
/// 
/// Usage: WN_RETURN_COMMAND_ERROR_ARRAY_RESPONSE(WN_JSON_RPC_ERROR_INVALID_ARGUMENTS, errorMessageArray);
/// 
/// Returns JSON-RPC 2.0 error response format:
/// {
///   "jsonrpc": "2.0",
///   "error": {
///     "code": -32002,
///     "message": "Invalid command arguments",
///     "data": [ "error1", "error2", ... ]
///   },
///   "id": "command_name"
/// }
/// 
/// @param InErrorCode The JSON-RPC 2.0 error code
/// @param InErrorDataValuePtrArray The error data array to include in 'data' field (TArray<TSharedPtr<FJsonValue>>)
#define WN_RETURN_COMMAND_ERROR_ARRAY_RESPONSE(InErrorCode, InErrorDataValuePtrArray) \
	TSharedPtr<FJsonObject> jsonErrorResponse = MakeShareable(new FJsonObject);\
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);\
	errorObj->SetNumberField(TEXT("code"), InErrorCode);\
	errorObj->SetStringField(TEXT("message"), WN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode));\
	errorObj->SetArrayField(TEXT("data"), InErrorDataValuePtrArray);\
	jsonErrorResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	jsonErrorResponse->SetObjectField(TEXT("error"), errorObj);\
	jsonErrorResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonErrorResponse

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup
//-----------------------------------------------------------------------------

/// Base class for MCP commands.
class FWN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	WN_MCP_API FWN_MCP_CommandGroup();

	/// destructor.
	WN_MCP_API virtual ~FWN_MCP_CommandGroup();

	/// Get command group name.
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @return name.
	WN_MCP_API virtual FString GetName() const;

	/// Get application name used as command name prefix.
	/// Override in derived classes to set the prefix (e.g. "WN_MCP_WORLD").
	/// @return application name. Empty string means no prefix.
	WN_MCP_API virtual FString GetApplicationName() const;

	/// Called when the commands is registered, allowing it to add its info to the list of available commands.
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @param InOutCommandInfos List of available command infos, which the command can add its info to.
	WN_MCP_API virtual void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const;

	/// Execute the command with given parameters and client socket. 
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @param InCommandName command name.
	/// @param InParamsPtr Command parameters, passed as a JSON object.
	/// @param InClientSocketPtr Socket of the client that sent the command, which can be used for sending responses or further communication.
	/// @return JSON object containing the result of command execution, which will be serialized and sent back to the client as a response.
	WN_MCP_API virtual TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const;

private:

	friend class FWN_MCP_Module;

	/// Execute the command with given parameters and client socket.
	/// @param InCommandName command name.
	/// @param InParamsPtr Command parameters, passed as a JSON object.
	/// @param InClientSocketPtr Socket of the client that sent the command, which can be used for sending responses or further communication.
	/// @return JSON object containing the result of command execution, which will be serialized and sent back to the client as a response.
	TSharedPtr<FJsonObject> Execute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const;
};