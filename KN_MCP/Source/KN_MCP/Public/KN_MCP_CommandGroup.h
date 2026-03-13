#pragma once

#include "CoreMinimal.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class FSocket;
class FJsonObject;

//-----------------------------------------------------------------------------
// FKN_MCP_CommandInfo
//-----------------------------------------------------------------------------

/// Command registration info.
struct FKN_MCP_CommandInfo
{
	FString Name;
	FString Description;
	bool bIsSimple = false;
};

//-----------------------------------------------------------------------------
// Defines
//-----------------------------------------------------------------------------

/*
	JSON-RPC 2.0 Request Format:
	{
		"jsonrpc": "2.0",
		"method": "command_name",
		"params": { ... },
		"id": "<unique_request_id>"
	}

	- "method": command name used for routing (e.g. "Actor_get_actors_in_level")
	- "id": unique request identifier (e.g. UUID), echoed back in the response for correlation

	JSON-RPC 2.0 Success Response Format:
	{
		"jsonrpc": "2.0",
		"result": {
			"key1": "value1",
			"key2": "value2",
			...
		},
		"id": "<unique_request_id>"
	}

	JSON-RPC 2.0 Error Response Format:
	{
		"jsonrpc": "2.0",
		"error": {
			"code": -32600,
			"message": "Invalid Request",
			"data": "additional error information"
		},
		"id": "<unique_request_id>"
	}

	Error Code Standards:
	- code: must be an integer
	- message: must be a string providing a short description of the error
	- data: may contain a primitive or structured value that contains additional information about the error (optional)
*/

/// Register MCP command group.
#define KN_MCP_REGISTER_COMMAND_GROUP(CommandGroupClass) class RegisterCommandGroup_ ##CommandGroupClass\
{\
public:\
	RegisterCommandGroup_ ##CommandGroupClass()\
	{\
		TSharedPtr<CommandGroupClass> commandGroupPtr = MakeShared<CommandGroupClass>();\
		FKN_MCP_Module::RegisterCommandGroup(commandGroupPtr);\
	}\
};\
static RegisterCommandGroup_ ##CommandGroupClass RegisterCommandGroupInstance_ ##CommandGroupClass

/// Register a command (requires custom Python Tool with docstring as description).
/// GetName() prefix is prepended automatically (e.g. "Actor" + "_" + "spawn_actor" = "Actor_spawn_actor").
#define KN_MCP_REGISTER_COMMAND(InOutList, CommandName) \
	InOutList.Add({ GetName() + TEXT("_") + FString(TEXT(CommandName)), FString(TEXT("")), false })

/// Register a simple command (Python Tool auto-generated).
/// GetName() prefix is prepended automatically (e.g. "Actor" + "_" + "spawn_actor" = "Actor_spawn_actor").
#define KN_MCP_REGISTER_SIMPLE_COMMAND(InOutList, CommandName, CommandDesc) \
	InOutList.Add({ GetName() + TEXT("_") + FString(TEXT(CommandName)), FString(TEXT(CommandDesc)), true })

/// Parse error - Invalid JSON was received by the server.
#define KN_JSON_RPC_ERROR_PARSE_ERROR -32700

/// Invalid Request - The JSON sent is not a valid Request object.
#define KN_JSON_RPC_ERROR_INVALID_REQUEST -32600

/// Method not found - The method does not exist / is not available.
#define KN_JSON_RPC_ERROR_METHOD_NOT_FOUND -32601

/// Invalid params - Invalid method parameter(s).
#define KN_JSON_RPC_ERROR_INVALID_PARAMS -32602

/// Internal error - Internal JSON-RPC error.
#define KN_JSON_RPC_ERROR_INTERNAL_ERROR -32603

/// Server error - Reserved for implementation-defined server errors (-32768 to -32000).
#define KN_JSON_RPC_ERROR_SERVER_ERROR -32000

/// Custom error - Command execution failed.
#define KN_JSON_RPC_ERROR_COMMAND_FAILED -32001

/// Custom error - Invalid command arguments.
#define KN_JSON_RPC_ERROR_INVALID_ARGUMENTS -32002

/// Custom error - Unreal Engine communication error.
#define KN_JSON_RPC_ERROR_UE_COMMUNICATION_ERROR -32003

/// Get error message for JSON-RPC 2.0 error code.
#define KN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode) \
	(InErrorCode == KN_JSON_RPC_ERROR_PARSE_ERROR ? TEXT("Parse error") : \
	 InErrorCode == KN_JSON_RPC_ERROR_INVALID_REQUEST ? TEXT("Invalid Request") : \
	 InErrorCode == KN_JSON_RPC_ERROR_METHOD_NOT_FOUND ? TEXT("Method not found") : \
	 InErrorCode == KN_JSON_RPC_ERROR_INVALID_PARAMS ? TEXT("Invalid params") : \
	 InErrorCode == KN_JSON_RPC_ERROR_INTERNAL_ERROR ? TEXT("Internal error") : \
	 InErrorCode == KN_JSON_RPC_ERROR_SERVER_ERROR ? TEXT("Server error") : \
	 InErrorCode == KN_JSON_RPC_ERROR_COMMAND_FAILED ? TEXT("Command execution failed") : \
	 InErrorCode == KN_JSON_RPC_ERROR_INVALID_ARGUMENTS ? TEXT("Invalid command arguments") : \
	 InErrorCode == KN_JSON_RPC_ERROR_UE_COMMUNICATION_ERROR ? TEXT("Unreal Engine communication error") : \
	 TEXT("Unknown error"))

/// Return command response with given result following JSON-RPC 2.0 success format.
/// 
/// The 'id' field is set to InCommandName to identify which command generated the response.
/// The 'result' field contains the command execution result.
/// 
/// Usage: KN_RETURN_COMMAND_RESPONSE(InResultPtr);
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
#define KN_RETURN_COMMAND_RESPONSE(InJsonResultObjectPtr) \
	TSharedPtr<FJsonObject> jsonResponse = MakeShareable(new FJsonObject);\
	jsonResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	if ((InJsonResultObjectPtr).IsValid())\
	{\
		jsonResponse->SetObjectField(TEXT("result"), (InJsonResultObjectPtr));\
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
/// Usage: KN_RETURN_COMMAND_ARRAY_RESPONSE(jsonArrayValues);
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
#define KN_RETURN_COMMAND_ARRAY_RESPONSE(InJsonResultValuePtrArray) \
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
/// Usage: KN_RETURN_COMMAND_TEXT_RESPONSE(TEXT("Command executed successfully"));
/// 
/// Returns JSON-RPC 2.0 success response format:
/// {
///   "jsonrpc": "2.0",
///   "result": "Command executed successfully",
///   "id": "command_name"
/// }
/// 
/// @param InResultMessage The result message to include in the 'result' field (const TCHAR*)
#define KN_RETURN_COMMAND_TEXT_RESPONSE(InResultMessage) \
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
/// Usage: KN_RETURN_COMMAND_ERROR_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, InErrorDataObjectPtr);
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
#define KN_RETURN_COMMAND_ERROR_RESPONSE(InErrorCode, InErrorDataObjectPtr) \
	TSharedPtr<FJsonObject> jsonErrorResponse = MakeShareable(new FJsonObject);\
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);\
	errorObj->SetNumberField(TEXT("code"), InErrorCode);\
	errorObj->SetStringField(TEXT("message"), KN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode));\
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
/// Usage: KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing 'message' parameter"));
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
#define KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(InErrorCode, InErrorMessage) \
	TSharedPtr<FJsonObject> jsonErrorResponse = MakeShareable(new FJsonObject);\
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);\
	errorObj->SetNumberField(TEXT("code"), InErrorCode);\
	errorObj->SetStringField(TEXT("message"), KN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode));\
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
/// Usage: KN_RETURN_COMMAND_ERROR_ARRAY_RESPONSE(KN_JSON_RPC_ERROR_INVALID_ARGUMENTS, errorMessageArray);
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
#define KN_RETURN_COMMAND_ERROR_ARRAY_RESPONSE(InErrorCode, InErrorDataValuePtrArray) \
	TSharedPtr<FJsonObject> jsonErrorResponse = MakeShareable(new FJsonObject);\
	TSharedPtr<FJsonObject> errorObj = MakeShareable(new FJsonObject);\
	errorObj->SetNumberField(TEXT("code"), InErrorCode);\
	errorObj->SetStringField(TEXT("message"), KN_GET_JSON_RPC_ERROR_MESSAGE(InErrorCode));\
	errorObj->SetArrayField(TEXT("data"), InErrorDataValuePtrArray);\
	jsonErrorResponse->SetStringField(TEXT("jsonrpc"), TEXT("2.0"));\
	jsonErrorResponse->SetObjectField(TEXT("error"), errorObj);\
	jsonErrorResponse->SetStringField(TEXT("id"), InCommandName);\
	return jsonErrorResponse

// =============================================================================
// KN_MCP_CREATE_RESULT_XXX — result object builders
//
// These macros create a TSharedPtr<FJsonObject> that represents the inner
// 'result' payload for a JSON-RPC 2.0 success response.
// Pass the return value directly to KN_RETURN_COMMAND_RESPONSE().
//
// Each macro corresponds to one of the agent-chain cases defined in
// Docs/MCP-UE-Agent-Chain-Case-Study.md.
// =============================================================================

/// Case 2 / Case 7 — Delegation execution (run_required)
///
/// UE instructs the agent to run an external command and report the result back
/// via a paired <tool>_result call.
///
/// result.status  = "run_required"
/// result.command : full command line the agent must execute
/// result.message : human-readable instruction shown to the agent
/// (set any additional parameter fields directly on the returned object)
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       FString cmd = FString::Printf(
///           TEXT("uv run python movie_to_fbx.py --skeleton_path %s --movie_path %s"),
///           *skeletonPath, *moviePath);
///
///       auto result = KN_MCP_CREATE_RESULT_RUN_REQUIRED(
///           cmd,
///           TEXT("Run the command below, then report result via movie_to_fbx_result."));
///       result->SetStringField(TEXT("skeleton_path"), skeletonPath);
///
///       KN_RETURN_COMMAND_RESPONSE(result);
///   }
///
/// @param InCommand  Full command line string (FString or const TCHAR*)
/// @param InMessage  Instruction text shown to the agent (FString or const TCHAR*)
#define KN_MCP_CREATE_RESULT_RUN_REQUIRED(InCommand, InMessage) \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetStringField(TEXT("status"),  TEXT("run_required")); \
		_r->SetStringField(TEXT("message"), (InMessage)); \
		_r->SetStringField(TEXT("command"), (InCommand)); \
		return _r; \
	}()

/// Case 3 — Async task accepted (accepted)
///
/// The task has been accepted and is now running in the background.
/// The agent must poll get_task_result or wait for a completion notification.
///
/// result.status     = "accepted"
/// result.request_id : opaque token used to identify this job in follow-up calls
/// result.message    : human-readable status hint for the agent
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       FString RequestId = FGuid::NewGuid().ToString();
///       LaunchBackgroundBake(RequestId);
///
///       KN_RETURN_COMMAND_RESPONSE(KN_MCP_CREATE_RESULT_ACCEPTED(
///           RequestId,
///           TEXT("Bake started. Poll get_task_result or wait for notification.")));
///   }
///
/// @param InRequestId  Unique job identifier (FString or const TCHAR*)
/// @param InMessage    Status hint for the agent (FString or const TCHAR*)
#define KN_MCP_CREATE_RESULT_ACCEPTED(InRequestId, InMessage) \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetStringField(TEXT("status"),     TEXT("accepted")); \
		_r->SetStringField(TEXT("request_id"), (InRequestId)); \
		_r->SetStringField(TEXT("message"),    (InMessage)); \
		return _r; \
	}()

/// Case 3 — Async task still running (running)
///
/// The agent polled for a result but the job has not finished yet.
///
/// result.status     = "running"
/// result.request_id : same token returned by the accepted response
/// result.progress   : 0.0–1.0 completion estimate (pass negative to omit)
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       FString RequestId = InParamsPtr->GetStringField(TEXT("request_id"));
///       float Progress = GetBakeProgress(RequestId);
///
///       KN_RETURN_COMMAND_RESPONSE(KN_MCP_CREATE_RESULT_RUNNING(RequestId, Progress));
///   }
///
/// @param InRequestId  Unique job identifier (FString or const TCHAR*)
/// @param InProgress   Completion fraction in [0, 1]; pass negative to omit the field
#define KN_MCP_CREATE_RESULT_RUNNING(InRequestId, InProgress) \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetStringField(TEXT("status"),     TEXT("running")); \
		_r->SetStringField(TEXT("request_id"), (InRequestId)); \
		if ((InProgress) >= 0.0f) { _r->SetNumberField(TEXT("progress"), (InProgress)); } \
		return _r; \
	}()

/// Case 3 — Async task completed (completed)
///
/// The background job finished successfully.
/// Set any output data fields directly on the returned object.
///
/// result.status     = "completed"
/// result.request_id : same token returned by the accepted response
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       FString requestId = InParamsPtr->GetStringField(TEXT("request_id"));
///
///       auto result = KN_MCP_CREATE_RESULT_COMPLETED(requestId);
///       result->SetNumberField(TEXT("duration_sec"), 120.0);
///       result->SetStringField(TEXT("output_path"), TEXT("F:\\Baked\\Scene.umap"));
///
///       KN_RETURN_COMMAND_RESPONSE(result);
///   }
///
/// @param InRequestId  Unique job identifier (FString or const TCHAR*)
#define KN_MCP_CREATE_RESULT_COMPLETED(InRequestId) \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetStringField(TEXT("status"),     TEXT("completed")); \
		_r->SetStringField(TEXT("request_id"), (InRequestId)); \
		return _r; \
	}()

/// Case 2 — Script result acknowledged (received)
///
/// Response to a <tool>_result report call. Tells the agent that UE has
/// received and processed the script output.
///
/// Produces: { "received": true }
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       bool bSuccess = InParamsPtr->GetBoolField(TEXT("success"));
///       if (bSuccess)
///       {
///           FString FbxPath = InParamsPtr->GetStringField(TEXT("fbx_path"));
///           ApplyFbxToSequencer(FbxPath);
///       }
///
///       KN_RETURN_COMMAND_RESPONSE(KN_MCP_CREATE_RESULT_RECEIVED());
///   }
#define KN_MCP_CREATE_RESULT_RECEIVED() \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetBoolField(TEXT("received"), true); \
		return _r; \
	}()

/// Chained tool call required (follow_up_required)
///
/// Returned when UE wants the agent to immediately call another MCP tool.
/// Set then_params and any other fields directly on the returned object.
///
/// result.status      = "follow_up_required"
/// result.then_method : name of the MCP tool the agent must call next
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       TSharedPtr<FJsonObject> thenParams = MakeShareable(new FJsonObject);
///       thenParams->SetStringField(TEXT("fbx_path"), fbxPath);
///
///       auto result = KN_MCP_CREATE_RESULT_FOLLOW_UP_REQUIRED(TEXT("Actor_import_fbx"));
///       result->SetObjectField(TEXT("then_params"), thenParams);
///
///       KN_RETURN_COMMAND_RESPONSE(result);
///   }
///
/// @param InThenMethod  Name of the MCP tool to call next (FString or const TCHAR*)
#define KN_MCP_CREATE_RESULT_FOLLOW_UP_REQUIRED(InThenMethod) \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetStringField(TEXT("status"),      TEXT("follow_up_required")); \
		_r->SetStringField(TEXT("then_method"), (InThenMethod)); \
		return _r; \
	}()

/// Multi-step workflow hint (suggested_tool)
///
/// A pipeline step returns its result AND hints which tool to call next.
/// Set step result fields and params_for_next directly on the returned object.
///
/// result.suggested_tool : name of the tool the agent should call next
///
/// Code snippet:
///
///   TSharedPtr<FJsonObject> OnExecute(...) const override
///   {
///       TSharedPtr<FJsonObject> paramsForNext = MakeShareable(new FJsonObject);
///       paramsForNext->SetStringField(TEXT("movie_path"), moviePath);
///
///       auto result = KN_MCP_CREATE_RESULT_WITH_SUGGESTED_TOOL(TEXT("movie_to_fbx"));
///       result->SetStringField(TEXT("movie_path"), moviePath);
///       result->SetObjectField(TEXT("params_for_next"), paramsForNext);
///
///       KN_RETURN_COMMAND_RESPONSE(result);
///   }
///
/// @param InSuggestedTool  Name of the recommended next tool (FString or const TCHAR*)
#define KN_MCP_CREATE_RESULT_WITH_SUGGESTED_TOOL(InSuggestedTool) \
	[&]() -> TSharedPtr<FJsonObject> \
	{ \
		TSharedPtr<FJsonObject> _r = MakeShareable(new FJsonObject); \
		_r->SetStringField(TEXT("suggested_tool"), (InSuggestedTool)); \
		return _r; \
	}()

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup
//-----------------------------------------------------------------------------

/// Base class for MCP commands.
class FKN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	KN_MCP_API FKN_MCP_CommandGroup();

	/// destructor.
	KN_MCP_API virtual ~FKN_MCP_CommandGroup();

	/// Get command group name.
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @return name.
	KN_MCP_API virtual FString GetName() const;

	/// Get application name used as command name prefix.
	/// Override in derived classes to set the prefix (e.g. "KN_MCP_EXTENSION").
	/// @return application name. Empty string means no prefix.
	KN_MCP_API virtual FString GetApplicationName() const;

	/// Called when the commands is registered, allowing it to add its info to the list of available commands.
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @param InOutCommandInfos List of available command infos, which the command can add its info to.
	KN_MCP_API virtual void OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const;

	/// Execute the command with given parameters and client socket. 
	/// This is a virtual function that must be implemented by derived classes to define the specific behavior of the command.
	/// @param InCommandName command name.
	/// @param InParamsPtr Command parameters, passed as a JSON object.
	/// @param InClientSocketPtr Socket of the client that sent the command, which can be used for sending responses or further communication.
	/// @return JSON object containing the result of command execution, which will be serialized and sent back to the client as a response.
	KN_MCP_API virtual TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const;

private:

	friend class FKN_MCP_Module;

	/// Execute the command with given parameters and client socket.
	/// @param InCommandName command name.
	/// @param InRequestId JSON-RPC 2.0 request id to echo back in response.
	/// @param InParamsPtr Command parameters, passed as a JSON object.
	/// @param InClientSocketPtr Socket of the client that sent the command, which can be used for sending responses or further communication.
	/// @return JSON object containing the result of command execution, which will be serialized and sent back to the client as a response.
	TSharedPtr<FJsonObject> Execute(const FString& InCommandName, const FString& InRequestId, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const;
};