#include "WN_MCP_WORLD_Module.h"
#include "WN_MCP_Module.h"

#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCPWorld);

//-----------------------------------------------------------------------------
// Statics
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_WORLD_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FWN_MCP_WORLD_Module"

void FWN_MCP_WORLD_Module::StartupModule()
{
	UE_LOG(LogMCPWorld, Display, TEXT("WemadeNext MCP World Module has started"));

	FWN_MCP_Module& mcpModule = FWN_MCP_Module::Get();
	FString pythonDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir() + TEXT("WN_MCP_WORLD/Python/tools"));
	FPaths::MakePlatformFilename(pythonDir);
	mcpModule.AddUserToolDirectories({ pythonDir });
}

void FWN_MCP_WORLD_Module::ShutdownModule()
{
	UE_LOG(LogMCPWorld, Display, TEXT("WemadeNext MCP World Module has shut down"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FWN_MCP_WORLD_Module, WN_MCP_WORLD)
