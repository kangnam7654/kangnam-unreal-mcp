#include "WN_MCP_WORLD_Editor_Module.h"

#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCPWorldEditor);

//-----------------------------------------------------------------------------
// Statics
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_WORLD_Editor_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FWN_MCP_WORLD_Editor_Module"

void FWN_MCP_WORLD_Editor_Module::StartupModule()
{
	UE_LOG(LogMCPWorldEditor, Display, TEXT("Kangnam Kim MCP World Editor Module has started"));
}

void FWN_MCP_WORLD_Editor_Module::ShutdownModule()
{
	UE_LOG(LogMCPWorldEditor, Display, TEXT("Kangnam Kim MCP World Editor Module has shut down"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FWN_MCP_WORLD_Editor_Module, WN_MCP_WORLD_Editor)
