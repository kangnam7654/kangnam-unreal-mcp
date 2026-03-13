#include "KN_MCPTest_Module.h"
#include "KN_MCP_Module.h"

#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCPTest);

//-----------------------------------------------------------------------------
// FKN_MCPTest_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FKN_MCPTest_Module"

void FKN_MCPTest_Module::StartupModule()
{
	UE_LOG(LogMCPTest, Display, TEXT("KN_MCPTest Module has started"));

	FKN_MCP_Module& mcpModule = FKN_MCP_Module::Get();
	FString pythonDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir() + TEXT("KN_MCPTest/Python"));
	FPaths::MakePlatformFilename(pythonDir);
	mcpModule.AddUserToolDirectories({ pythonDir });
}

void FKN_MCPTest_Module::ShutdownModule()
{
	UE_LOG(LogMCPTest, Display, TEXT("KN_MCPTest Module has shut down"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FKN_MCPTest_Module, KN_MCPTest)
