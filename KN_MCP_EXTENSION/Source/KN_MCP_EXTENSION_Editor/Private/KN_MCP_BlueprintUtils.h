#pragma once

#include "CoreMinimal.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

class UBlueprint;
class USCS_Node;

//-----------------------------------------------------------------------------
// FKN_MCP_BlueprintUtils
//-----------------------------------------------------------------------------

/// Shared utility functions for Blueprint operations.
class FKN_MCP_BlueprintUtils
{
public:

	/// Find a Blueprint asset by name or full path.
	/// Tries LoadObject -> AssetRegistry -> FindObject fallback.
	/// @param InBlueprintName Blueprint name (e.g. "MyBP") or full path (e.g. "/Game/Blueprints/MyBP").
	/// @return Blueprint object, or nullptr if not found.
	static UBlueprint* FindBlueprintByName(const FString& InBlueprintName);

	/// Find an SCS (Simple Construction Script) node by component variable name.
	/// @param InBlueprint Blueprint to search in.
	/// @param InComponentName Component variable name (e.g. "Mesh1").
	/// @return SCS node, or nullptr if not found.
	static USCS_Node* FindSCSNodeByName(UBlueprint* InBlueprint, const FString& InComponentName);
};
