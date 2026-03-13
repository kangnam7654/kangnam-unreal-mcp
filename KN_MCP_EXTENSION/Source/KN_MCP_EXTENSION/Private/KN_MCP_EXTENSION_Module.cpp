#include "KN_MCP_EXTENSION_Module.h"
#include "KN_MCP_Module.h"

#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCPExtension);

//-----------------------------------------------------------------------------
// Statics
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FKN_MCP_EXTENSION_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FKN_MCP_EXTENSION_Module"

void FKN_MCP_EXTENSION_Module::StartupModule()
{
	UE_LOG(LogMCPExtension, Display, TEXT("KN_MCP_EXTENSION Module has started"));

	FKN_MCP_Module& mcpModule = FKN_MCP_Module::Get();
	FString pythonDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir() + TEXT("KN_MCP_EXTENSION/Python/tools"));
	FPaths::MakePlatformFilename(pythonDir);
	mcpModule.AddUserToolDirectories({ pythonDir });
}

void FKN_MCP_EXTENSION_Module::ShutdownModule()
{
	UE_LOG(LogMCPExtension, Display, TEXT("KN_MCP_EXTENSION Module has shut down"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FKN_MCP_EXTENSION_Module, KN_MCP_EXTENSION)
