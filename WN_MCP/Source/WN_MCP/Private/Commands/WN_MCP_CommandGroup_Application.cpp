#include "WN_MCP_CommandGroup_Application.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Application
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Application);

FWN_MCP_CommandGroup_Application::FWN_MCP_CommandGroup_Application()
{

}

FWN_MCP_CommandGroup_Application::~FWN_MCP_CommandGroup_Application()
{
}

FString FWN_MCP_CommandGroup_Application::GetName() const
{
	return FString("Application");
}

void FWN_MCP_CommandGroup_Application::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("get_user_tool_directories")));

}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Application::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	FWN_MCP_Module& module = FWN_MCP_Module::Get();

	if (InCommandName == FString(TEXT("get_user_tool_directories")))
	{
		const TArray<FString>& userToolDirs = module.GetUserToolDirectories();
		TArray<TSharedPtr<FJsonValue>> jsonUserToolDirValues;
		for (const FString& dir : userToolDirs)
		{
			jsonUserToolDirValues.Add(MakeShareable(new FJsonValueString(dir)));
		}
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetArrayField(TEXT("directories"), jsonUserToolDirValues);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}