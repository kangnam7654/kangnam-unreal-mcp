#include "WN_MCP_CommandGroup_Test.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FWN_MCP_Command
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Test);

FWN_MCP_CommandGroup_Test::FWN_MCP_CommandGroup_Test()
{

}

FWN_MCP_CommandGroup_Test::~FWN_MCP_CommandGroup_Test()
{
}

FString FWN_MCP_CommandGroup_Test::GetName() const
{
	return FString("Test");
}

void FWN_MCP_CommandGroup_Test::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add("get_hello_message");
	InOutCommandNames.Add("get_hello_message_array");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Test::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	if (InCommandName == FString(TEXT("get_hello_message")))
	{
		WN_RETURN_COMMAND_TEXT_RESPONSE(*FString::Printf(TEXT("Hello from UE : %d."), FWN_MCP_Module::Get().GetListenerPort()));
	}
	else if(InCommandName == FString(TEXT("get_hello_message_array")))
	{
		TArray<TSharedPtr<FJsonValue>> jsonHelloMessageValues;
		jsonHelloMessageValues.Add(MakeShareable(new FJsonValueString(TEXT("Hello from Unreal Editor 1!"))));
		jsonHelloMessageValues.Add(MakeShareable(new FJsonValueString(TEXT("Hello from Unreal Editor 2!"))));
		jsonHelloMessageValues.Add(MakeShareable(new FJsonValueString(TEXT("Hello from Unreal Editor 3!"))));
		WN_RETURN_COMMAND_ARRAY_RESPONSE(jsonHelloMessageValues);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}