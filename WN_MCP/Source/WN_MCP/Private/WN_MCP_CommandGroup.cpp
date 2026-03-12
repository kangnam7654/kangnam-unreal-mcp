#include "WN_MCP_CommandGroup.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FWN_MCP_Command
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup);

FWN_MCP_CommandGroup::FWN_MCP_CommandGroup()
{

}

FWN_MCP_CommandGroup::~FWN_MCP_CommandGroup()
{
}

FString FWN_MCP_CommandGroup::GetName() const
{
	return FString("Unknown");
}

FString FWN_MCP_CommandGroup::GetApplicationName() const
{
	return FString("");
}

void FWN_MCP_CommandGroup::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	__noop;
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	ensureAlways(false); // should be overridden by derived class.
	return TSharedPtr<FJsonObject>();
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup::Execute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	// Strip GetName() prefix before passing to OnExecute
	FString appName = GetName();
	FString rawCommandName = InCommandName;
	if (!appName.IsEmpty())
	{
		FString prefix = appName + TEXT("_");
		rawCommandName.RemoveFromStart(prefix);
	}

	return OnExecute(rawCommandName, InParamsPtr, InClientSocketPtr);
}