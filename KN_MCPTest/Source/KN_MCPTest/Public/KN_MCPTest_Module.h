#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FKN_MCPTest_Module
//-----------------------------------------------------------------------------

/// Module class for KN_MCPTest plugin.
class FKN_MCPTest_Module : public IModuleInterface
{
	//-------------------------------------------------------------------------
	// IModuleInterface overrides
	//-------------------------------------------------------------------------

public:

	/// Startup module.
	virtual void StartupModule() override;

	/// Shutdown module.
	virtual void ShutdownModule() override;
};

//-----------------------------------------------------------------------------
// Log
//-----------------------------------------------------------------------------

DECLARE_LOG_CATEGORY_EXTERN(LogMCPTest, Log, All);
