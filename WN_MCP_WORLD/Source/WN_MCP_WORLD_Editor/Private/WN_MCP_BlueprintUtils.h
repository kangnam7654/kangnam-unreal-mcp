#pragma once

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class UBlueprint;

//-----------------------------------------------------------------------------
// FWN_MCP_BlueprintUtils
//-----------------------------------------------------------------------------

/// Shared utility functions for Blueprint operations.
class FWN_MCP_BlueprintUtils
{
public:

	/// Find a Blueprint asset by name or full path.
	/// Tries LoadObject -> AssetRegistry -> FindObject fallback.
	/// @param InBlueprintName Blueprint name (e.g. "MyBP") or full path (e.g. "/Game/Blueprints/MyBP").
	/// @return Blueprint object, or nullptr if not found.
	static UBlueprint* FindBlueprintByName(const FString& InBlueprintName);
};
