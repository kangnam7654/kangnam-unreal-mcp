#include "WN_MCP_BlueprintUtils.h"

#include "Engine/Blueprint.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "AssetRegistry/AssetRegistryModule.h"

//-----------------------------------------------------------------------------
// FWN_MCP_BlueprintUtils
//-----------------------------------------------------------------------------

UBlueprint* FWN_MCP_BlueprintUtils::FindBlueprintByName(const FString& InBlueprintName)
{
	FString objectPath;

	// Check if it's already a full path
	if (InBlueprintName.StartsWith(TEXT("/")))
	{
		FString assetName = FPaths::GetBaseFilename(InBlueprintName);
		objectPath = FString::Printf(TEXT("%s.%s"), *InBlueprintName, *assetName);
	}
	else
	{
		objectPath = FString::Printf(TEXT("/Game/Blueprints/%s.%s"), *InBlueprintName, *InBlueprintName);
	}

	// Try direct load first
	UBlueprint* blueprint = LoadObject<UBlueprint>(nullptr, *objectPath);
	if (blueprint)
	{
		return blueprint;
	}

	// Try asset registry
	FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
	FAssetData assetData = assetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(objectPath));

	if (assetData.IsValid())
	{
		blueprint = Cast<UBlueprint>(assetData.GetAsset());
		if (blueprint)
		{
			return blueprint;
		}
	}

	// Fallback: in-memory search
	FString packagePath = TEXT("/Game/Blueprints/") + InBlueprintName;
	blueprint = FindObject<UBlueprint>(nullptr, *packagePath);

	return blueprint;
}

USCS_Node* FWN_MCP_BlueprintUtils::FindSCSNodeByName(UBlueprint* InBlueprint, const FString& InComponentName)
{
	if (!InBlueprint || !InBlueprint->SimpleConstructionScript)
	{
		return nullptr;
	}

	for (USCS_Node* node : InBlueprint->SimpleConstructionScript->GetAllNodes())
	{
		if (node && node->GetVariableName().ToString() == InComponentName)
		{
			return node;
		}
	}

	return nullptr;
}
