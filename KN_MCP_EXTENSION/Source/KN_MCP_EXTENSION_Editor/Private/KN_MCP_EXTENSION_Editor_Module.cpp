#include "KN_MCP_EXTENSION_Editor_Module.h"

#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DEFINE_LOG_CATEGORY(LogMCPExtensionEditor);

//-----------------------------------------------------------------------------
// Statics
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FKN_MCP_EXTENSION_Editor_Module
//-----------------------------------------------------------------------------

#define LOCTEXT_NAMESPACE "FKN_MCP_EXTENSION_Editor_Module"

void FKN_MCP_EXTENSION_Editor_Module::StartupModule()
{
	UE_LOG(LogMCPExtensionEditor, Display, TEXT("KN_MCP_EXTENSION_Editor Module has started"));
}

void FKN_MCP_EXTENSION_Editor_Module::ShutdownModule()
{
	UE_LOG(LogMCPExtensionEditor, Display, TEXT("KN_MCP_EXTENSION_Editor Module has shut down"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FKN_MCP_EXTENSION_Editor_Module, KN_MCP_EXTENSION_Editor)
