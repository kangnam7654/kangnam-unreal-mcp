#include "KN_MCP_CommandGroup.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FKN_MCP_Command
//-----------------------------------------------------------------------------

// NOTE: Base class must NOT self-register. Only derived command groups should use KN_MCP_REGISTER_COMMAND_GROUP.

FKN_MCP_CommandGroup::FKN_MCP_CommandGroup()
{

}

FKN_MCP_CommandGroup::~FKN_MCP_CommandGroup()
{
}

FString FKN_MCP_CommandGroup::GetName() const
{
	return FString("Unknown");
}

FString FKN_MCP_CommandGroup::GetApplicationName() const
{
	return FString("");
}

void FKN_MCP_CommandGroup::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	__noop;
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	ensureAlways(false); // should be overridden by derived class.
	return TSharedPtr<FJsonObject>();
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup::Execute(const FString& InCommandName, const FString& InRequestId, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	// Strip GetName() prefix before passing to OnExecute
	FString appName = GetName();
	FString rawCommandName = InCommandName;
	if (!appName.IsEmpty())
	{
		FString prefix = appName + TEXT("_");
		rawCommandName.RemoveFromStart(prefix);
	}

	TSharedPtr<FJsonObject> response = OnExecute(rawCommandName, InParamsPtr, InClientSocketPtr);

	// Set JSON-RPC 2.0 request id in response for correlation
	if (response.IsValid())
	{
		response->SetStringField(TEXT("id"), InRequestId);
	}

	return response;
}