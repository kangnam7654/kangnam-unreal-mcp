#include "WN_MCP_CommandGroup_StaticMesh.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/StaticMesh.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_StaticMesh
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_StaticMesh);

FWN_MCP_CommandGroup_StaticMesh::FWN_MCP_CommandGroup_StaticMesh()
{

}

FWN_MCP_CommandGroup_StaticMesh::~FWN_MCP_CommandGroup_StaticMesh()
{

}

FString FWN_MCP_CommandGroup_StaticMesh::GetName() const
{
	return FString("StaticMesh");
}

FString FWN_MCP_CommandGroup_StaticMesh::GetApplicationName() const
{
	return FString("WN_MCP_WORLD");
}

void FWN_MCP_CommandGroup_StaticMesh::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_static_meshes");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "find_static_meshes_by_name");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_StaticMesh::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// get_static_meshes
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_static_meshes")))
	{
		// Optional parameters
		FString searchPath = TEXT("/Game/");
		if (InParamsPtr.IsValid())
		{
			InParamsPtr->TryGetStringField(TEXT("search_path"), searchPath);
		}

		bool bIncludeEngineMeshes = true;
		if (InParamsPtr.IsValid())
		{
			InParamsPtr->TryGetBoolField(TEXT("include_engine_meshes"), bIncludeEngineMeshes);
		}

		// Query AssetRegistry for static meshes
		FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
		IAssetRegistry& assetRegistry = assetRegistryModule.Get();

		FARFilter filter;
		filter.ClassPaths.Add(UStaticMesh::StaticClass()->GetClassPathName());
		filter.bRecursivePaths = true;
		filter.PackagePaths.Add(FName(*searchPath));

		if (bIncludeEngineMeshes)
		{
			filter.PackagePaths.Add(FName(TEXT("/Engine/")));
		}

		TArray<FAssetData> assetList;
		assetRegistry.GetAssets(filter, assetList);

		TArray<TSharedPtr<FJsonValue>> meshArray;
		for (const FAssetData& asset : assetList)
		{
			TSharedPtr<FJsonObject> meshObj = MakeShareable(new FJsonObject());
			meshObj->SetStringField(TEXT("name"), asset.AssetName.ToString());
			meshObj->SetStringField(TEXT("path"), asset.GetObjectPathString());
			meshObj->SetStringField(TEXT("package"), asset.PackageName.ToString());
			meshArray.Add(MakeShareable(new FJsonValueObject(meshObj)));
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), meshArray.Num());
		InResultPtr->SetArrayField(TEXT("static_meshes"), meshArray);
		InResultPtr->SetStringField(TEXT("search_path"), searchPath);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// find_static_meshes_by_name
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("find_static_meshes_by_name")))
	{
		// Get required parameters
		FString searchText;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("search_text"), searchText))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: search_text"));
		}

		// Optional: include engine meshes (default: true)
		bool bIncludeEngineMeshes = true;
		if (InParamsPtr.IsValid())
		{
			InParamsPtr->TryGetBoolField(TEXT("include_engine_meshes"), bIncludeEngineMeshes);
		}

		// Query AssetRegistry for static meshes
		FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
		IAssetRegistry& assetRegistry = assetRegistryModule.Get();

		FARFilter filter;
		filter.ClassPaths.Add(UStaticMesh::StaticClass()->GetClassPathName());
		filter.PackagePaths.Add(FName(TEXT("/Game/")));
		filter.bRecursivePaths = true;

		if (bIncludeEngineMeshes)
		{
			filter.PackagePaths.Add(FName(TEXT("/Engine/")));
		}

		TArray<FAssetData> assetList;
		assetRegistry.GetAssets(filter, assetList);

		TArray<TSharedPtr<FJsonValue>> meshArray;
		for (const FAssetData& asset : assetList)
		{
			if (asset.AssetName.ToString().Contains(searchText))
			{
				TSharedPtr<FJsonObject> meshObj = MakeShareable(new FJsonObject());
				meshObj->SetStringField(TEXT("name"), asset.AssetName.ToString());
				meshObj->SetStringField(TEXT("path"), asset.GetObjectPathString());
				meshObj->SetStringField(TEXT("package"), asset.PackageName.ToString());
				meshArray.Add(MakeShareable(new FJsonValueObject(meshObj)));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), meshArray.Num());
		InResultPtr->SetArrayField(TEXT("static_meshes"), meshArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
