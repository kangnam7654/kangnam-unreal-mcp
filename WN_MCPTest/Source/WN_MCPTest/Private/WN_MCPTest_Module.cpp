#include "WN_MCPTest_Module.h"
#include "WN_MCP_Module.h"

#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCPTest);

//-----------------------------------------------------------------------------
// Statics
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FWN_MCPTest_Module"

void FWN_MCPTest_Module::StartupModule()
{
	UE_LOG(LogMCPTest, Display, TEXT("Kangnam Kim MCPTest Module has started"));

	FWN_MCP_Module& mcpModule = FWN_MCP_Module::Get();
	FString pythonDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir() + TEXT("WN_MCPTest/Python"));
	FPaths::MakePlatformFilename(pythonDir);
	mcpModule.AddUserToolDirectories({ pythonDir });
}

void FWN_MCPTest_Module::ShutdownModule()
{
	UE_LOG(LogMCPTest, Display, TEXT("Kangnam Kim MCPTest Module has shut down"));
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FWN_MCPTest_Module, WN_MCPTest) 