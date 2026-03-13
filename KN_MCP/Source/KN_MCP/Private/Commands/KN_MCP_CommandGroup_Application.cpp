#include "KN_MCP_CommandGroup_Application.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_Application
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_Application);

FKN_MCP_CommandGroup_Application::FKN_MCP_CommandGroup_Application()
{

}

FKN_MCP_CommandGroup_Application::~FKN_MCP_CommandGroup_Application()
{
}

FString FKN_MCP_CommandGroup_Application::GetName() const
{
	return FString("Application");
}

void FKN_MCP_CommandGroup_Application::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_user_tool_directories");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_simple_commands");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_Application::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	FKN_MCP_Module& module = FKN_MCP_Module::Get();

	//-------------------------------------------------------------------------
	// get_user_tool_directories
	//-------------------------------------------------------------------------

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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// get_simple_commands
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_simple_commands")))
	{
		const TArray<FKN_MCP_CommandInfo>& allInfos = FKN_MCP_Module::GetAllCommandInfos();
		TArray<TSharedPtr<FJsonValue>> jsonCommands;
		for (const FKN_MCP_CommandInfo& info : allInfos)
		{
			if (info.bIsSimple)
			{
				TSharedPtr<FJsonObject> cmdObj = MakeShareable(new FJsonObject());
				cmdObj->SetStringField(TEXT("name"), info.Name);
				cmdObj->SetStringField(TEXT("description"), info.Description);
				jsonCommands.Add(MakeShareable(new FJsonValueObject(cmdObj)));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetArrayField(TEXT("commands"), jsonCommands);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}