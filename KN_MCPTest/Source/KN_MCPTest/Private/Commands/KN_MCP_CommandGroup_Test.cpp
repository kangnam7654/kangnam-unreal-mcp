#include "KN_MCP_CommandGroup_Test.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_Test
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_Test);

FKN_MCP_CommandGroup_Test::FKN_MCP_CommandGroup_Test()
{

}

FKN_MCP_CommandGroup_Test::~FKN_MCP_CommandGroup_Test()
{
}

FString FKN_MCP_CommandGroup_Test::GetName() const
{
	return FString("Test");
}

FString FKN_MCP_CommandGroup_Test::GetApplicationName() const
{
	return FString("KN_MCPTest");
}

void FKN_MCP_CommandGroup_Test::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_SIMPLE_COMMAND(InOutCommandInfos, "get_hello_message", "Get hello message from UE");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_hello_message_array");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_Test::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// get_hello_message
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_hello_message")))
	{
		KN_RETURN_COMMAND_TEXT_RESPONSE(*FString::Printf(TEXT("Hello from UE : %d."), FKN_MCP_Module::Get().GetListenerPort()));
	}

	//-------------------------------------------------------------------------
	// get_hello_message_array
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_hello_message_array")))
	{
		TArray<TSharedPtr<FJsonValue>> jsonHelloMessageValues;
		jsonHelloMessageValues.Add(MakeShareable(new FJsonValueString(TEXT("Hello from Unreal Editor 1!"))));
		jsonHelloMessageValues.Add(MakeShareable(new FJsonValueString(TEXT("Hello from Unreal Editor 2!"))));
		jsonHelloMessageValues.Add(MakeShareable(new FJsonValueString(TEXT("Hello from Unreal Editor 3!"))));
		KN_RETURN_COMMAND_ARRAY_RESPONSE(jsonHelloMessageValues);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
