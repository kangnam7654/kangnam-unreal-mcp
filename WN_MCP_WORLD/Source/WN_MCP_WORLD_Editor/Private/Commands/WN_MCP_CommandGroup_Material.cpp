#include "WN_MCP_CommandGroup_Material.h"
#include "WN_MCP_BlueprintUtils.h"
#include "WN_MCP_ActorUtils.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceConstant.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Modules/ModuleManager.h"

//-----------------------------------------------------------------------------
// Helper Functions
//-----------------------------------------------------------------------------

/// Get or create a PBR material with BaseColor, Metallic, and Roughness parameters.
/// The material is cached at /Game/MCP_Generated/M_MCP_PBR.
static UMaterial* GetOrCreateMCPPBRMaterial()
{
	static const TCHAR* AssetPath = TEXT("/Game/MCP_Generated/M_MCP_PBR");
	static const TCHAR* FullObjectPath = TEXT("/Game/MCP_Generated/M_MCP_PBR.M_MCP_PBR");

	// Try loading existing material first
	UMaterial* mat = LoadObject<UMaterial>(nullptr, FullObjectPath);
	if (mat)
	{
		return mat;
	}

	// Create package and material
	UPackage* package = CreatePackage(AssetPath);
	package->FullyLoad();

	mat = NewObject<UMaterial>(package, TEXT("M_MCP_PBR"), RF_Public | RF_Standalone);

	UMaterialEditorOnlyData* editorData = mat->GetEditorOnlyData();

	// BaseColor VectorParameter (default: White)
	UMaterialExpressionVectorParameter* baseColorParam = NewObject<UMaterialExpressionVectorParameter>(mat);
	baseColorParam->ParameterName = TEXT("BaseColor");
	baseColorParam->DefaultValue = FLinearColor::White;
	editorData->ExpressionCollection.Expressions.Add(baseColorParam);
	editorData->BaseColor.Connect(0, baseColorParam);

	// Metallic ScalarParameter (default: 0.0)
	UMaterialExpressionScalarParameter* metallicParam = NewObject<UMaterialExpressionScalarParameter>(mat);
	metallicParam->ParameterName = TEXT("Metallic");
	metallicParam->DefaultValue = 0.0f;
	editorData->ExpressionCollection.Expressions.Add(metallicParam);
	editorData->Metallic.Connect(0, metallicParam);

	// Roughness ScalarParameter (default: 0.5)
	UMaterialExpressionScalarParameter* roughnessParam = NewObject<UMaterialExpressionScalarParameter>(mat);
	roughnessParam->ParameterName = TEXT("Roughness");
	roughnessParam->DefaultValue = 0.5f;
	editorData->ExpressionCollection.Expressions.Add(roughnessParam);
	editorData->Roughness.Connect(0, roughnessParam);

	// Compile material
	mat->PreEditChange(nullptr);
	mat->PostEditChange();

	// Register and save
	FAssetRegistryModule::AssetCreated(mat);
	package->MarkPackageDirty();
	UEditorAssetLibrary::SaveAsset(AssetPath, false);

	return mat;
}

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Material
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Material);

FWN_MCP_CommandGroup_Material::FWN_MCP_CommandGroup_Material()
{

}

FWN_MCP_CommandGroup_Material::~FWN_MCP_CommandGroup_Material()
{
}

FString FWN_MCP_CommandGroup_Material::GetName() const
{
	return FString("Material");
}

FString FWN_MCP_CommandGroup_Material::GetApplicationName() const
{
	return FString("WN_MCP_WORLD");
}

void FWN_MCP_CommandGroup_Material::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_available_materials", "Get all available materials");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "apply_material_to_actor", "Apply a material to an actor");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "apply_material_to_blueprint", "Apply a material to a Blueprint");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_actor_material_info", "Get material info from an actor");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_blueprint_material_info", "Get material info from a Blueprint");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "set_mesh_material_color", "Set mesh material color");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Material::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// get_available_materials
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_available_materials")))
	{
		// Optional parameters
		FString searchPath = TEXT("/Game/");
		if (InParamsPtr.IsValid())
		{
			InParamsPtr->TryGetStringField(TEXT("search_path"), searchPath);
		}

		bool bIncludeEngineMaterials = true;
		if (InParamsPtr.IsValid())
		{
			InParamsPtr->TryGetBoolField(TEXT("include_engine_materials"), bIncludeEngineMaterials);
		}

		// Query AssetRegistry for materials
		FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
		IAssetRegistry& assetRegistry = assetRegistryModule.Get();

		FARFilter filter;
		filter.ClassPaths.Add(UMaterial::StaticClass()->GetClassPathName());
		filter.ClassPaths.Add(UMaterialInstanceConstant::StaticClass()->GetClassPathName());
		filter.bRecursivePaths = true;
		filter.PackagePaths.Add(FName(*searchPath));

		if (bIncludeEngineMaterials)
		{
			filter.PackagePaths.Add(FName(TEXT("/Engine/")));
		}

		TArray<FAssetData> assetList;
		assetRegistry.GetAssets(filter, assetList);

		TArray<TSharedPtr<FJsonValue>> materialArray;
		for (const FAssetData& asset : assetList)
		{
			TSharedPtr<FJsonObject> matObj = MakeShareable(new FJsonObject());
			matObj->SetStringField(TEXT("name"), asset.AssetName.ToString());
			matObj->SetStringField(TEXT("path"), asset.GetObjectPathString());
			matObj->SetStringField(TEXT("package"), asset.PackageName.ToString());
			matObj->SetStringField(TEXT("class"), asset.AssetClassPath.GetAssetName().ToString());
			materialArray.Add(MakeShareable(new FJsonValueObject(matObj)));
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), materialArray.Num());
		InResultPtr->SetArrayField(TEXT("materials"), materialArray);
		InResultPtr->SetStringField(TEXT("search_path"), searchPath);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// apply_material_to_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("apply_material_to_actor")))
	{
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("actor_name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: actor_name"));
		}

		FString materialPath;
		if (!InParamsPtr->TryGetStringField(TEXT("material_path"), materialPath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: material_path"));
		}

		// Optional material slot
		int32 materialSlot = 0;
		double slotValue;
		if (InParamsPtr->TryGetNumberField(TEXT("material_slot"), slotValue))
		{
			materialSlot = static_cast<int32>(slotValue);
		}

		// Find actor
		AActor* foundActor = FWN_MCP_ActorUtils::FindActorByName(actorName);
		if (!foundActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Load material
		UMaterialInterface* material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(materialPath));
		if (!material)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Material not found: %s"), *materialPath));
		}

		// Apply to all StaticMeshComponents on the actor
		TArray<UStaticMeshComponent*> meshComponents;
		foundActor->GetComponents<UStaticMeshComponent>(meshComponents);

		if (meshComponents.Num() == 0)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Actor '%s' has no StaticMeshComponents"), *actorName));
		}

		for (UStaticMeshComponent* meshComp : meshComponents)
		{
			meshComp->SetMaterial(materialSlot, material);
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("actor_name"), actorName);
		InResultPtr->SetStringField(TEXT("material_path"), materialPath);
		InResultPtr->SetNumberField(TEXT("material_slot"), materialSlot);
		InResultPtr->SetNumberField(TEXT("components_updated"), meshComponents.Num());
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// apply_material_to_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("apply_material_to_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString componentName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_name"), componentName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}

		FString materialPath;
		if (!InParamsPtr->TryGetStringField(TEXT("material_path"), materialPath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: material_path"));
		}

		// Optional material slot
		int32 materialSlot = 0;
		double slotValue;
		if (InParamsPtr->TryGetNumberField(TEXT("material_slot"), slotValue))
		{
			materialSlot = static_cast<int32>(slotValue);
		}

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript"));
		}

		USCS_Node* targetNode = FWN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName);
		if (!targetNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Cast to PrimitiveComponent
		UPrimitiveComponent* primComponent = Cast<UPrimitiveComponent>(targetNode->ComponentTemplate);
		if (!primComponent)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				TEXT("Component is not a PrimitiveComponent"));
		}

		// Load material
		UMaterialInterface* material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(materialPath));
		if (!material)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Material not found: %s"), *materialPath));
		}

		// Apply material
		primComponent->SetMaterial(materialSlot, material);
		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		InResultPtr->SetStringField(TEXT("material_path"), materialPath);
		InResultPtr->SetNumberField(TEXT("material_slot"), materialSlot);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// get_actor_material_info
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_actor_material_info")))
	{
		FString actorName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("actor_name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: actor_name"));
		}

		// Find actor
		AActor* foundActor = FWN_MCP_ActorUtils::FindActorByName(actorName);
		if (!foundActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Actor '%s' not found"), *actorName));
		}

		// Get material info from all StaticMeshComponents
		TArray<UStaticMeshComponent*> meshComponents;
		foundActor->GetComponents<UStaticMeshComponent>(meshComponents);

		TArray<TSharedPtr<FJsonValue>> slotArray;
		for (UStaticMeshComponent* meshComp : meshComponents)
		{
			int32 numMaterials = meshComp->GetNumMaterials();
			for (int32 i = 0; i < numMaterials; ++i)
			{
				TSharedPtr<FJsonObject> slotObj = MakeShareable(new FJsonObject());
				slotObj->SetNumberField(TEXT("slot"), i);
				slotObj->SetStringField(TEXT("component"), meshComp->GetName());

				UMaterialInterface* mat = meshComp->GetMaterial(i);
				if (mat)
				{
					slotObj->SetStringField(TEXT("material_name"), mat->GetName());
					slotObj->SetStringField(TEXT("material_path"), mat->GetPathName());
					slotObj->SetStringField(TEXT("material_class"), mat->GetClass()->GetName());
				}
				else
				{
					slotObj->SetStringField(TEXT("material_name"), TEXT("None"));
					slotObj->SetStringField(TEXT("material_path"), TEXT(""));
					slotObj->SetStringField(TEXT("material_class"), TEXT(""));
				}

				slotArray.Add(MakeShareable(new FJsonValueObject(slotObj)));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("actor_name"), actorName);
		InResultPtr->SetNumberField(TEXT("total_slots"), slotArray.Num());
		InResultPtr->SetArrayField(TEXT("material_slots"), slotArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// get_blueprint_material_info
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("get_blueprint_material_info")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString componentName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_name"), componentName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript"));
		}

		USCS_Node* targetNode = FWN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName);
		if (!targetNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Cast to StaticMeshComponent
		UStaticMeshComponent* meshComponent = Cast<UStaticMeshComponent>(targetNode->ComponentTemplate);
		if (!meshComponent)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				TEXT("Component is not a StaticMeshComponent"));
		}

		// Get material slot info
		bool bHasStaticMesh = (meshComponent->GetStaticMesh() != nullptr);
		TArray<TSharedPtr<FJsonValue>> slotArray;

		if (bHasStaticMesh)
		{
			int32 numSections = meshComponent->GetStaticMesh()->GetNumSections(0);
			for (int32 i = 0; i < numSections; ++i)
			{
				TSharedPtr<FJsonObject> slotObj = MakeShareable(new FJsonObject());
				slotObj->SetNumberField(TEXT("slot"), i);
				slotObj->SetStringField(TEXT("component"), componentName);

				UMaterialInterface* mat = meshComponent->GetMaterial(i);
				if (mat)
				{
					slotObj->SetStringField(TEXT("material_name"), mat->GetName());
					slotObj->SetStringField(TEXT("material_path"), mat->GetPathName());
					slotObj->SetStringField(TEXT("material_class"), mat->GetClass()->GetName());
				}
				else
				{
					slotObj->SetStringField(TEXT("material_name"), TEXT("None"));
					slotObj->SetStringField(TEXT("material_path"), TEXT(""));
					slotObj->SetStringField(TEXT("material_class"), TEXT(""));
				}

				slotArray.Add(MakeShareable(new FJsonValueObject(slotObj)));
			}
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		InResultPtr->SetBoolField(TEXT("has_static_mesh"), bHasStaticMesh);
		InResultPtr->SetNumberField(TEXT("total_slots"), slotArray.Num());
		InResultPtr->SetArrayField(TEXT("material_slots"), slotArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// set_mesh_material_color
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("set_mesh_material_color")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString componentName;
		if (!InParamsPtr->TryGetStringField(TEXT("component_name"), componentName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}

		// Color array [R, G, B, A] (0.0 - 1.0)
		const TArray<TSharedPtr<FJsonValue>>* colorArray;
		if (!InParamsPtr->TryGetArrayField(TEXT("color"), colorArray) || colorArray->Num() < 3)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				TEXT("Missing or invalid 'color' parameter (expected [R, G, B] or [R, G, B, A])"));
		}

		float r = static_cast<float>((*colorArray)[0]->AsNumber());
		float g = static_cast<float>((*colorArray)[1]->AsNumber());
		float b = static_cast<float>((*colorArray)[2]->AsNumber());
		float a = (colorArray->Num() >= 4) ? static_cast<float>((*colorArray)[3]->AsNumber()) : 1.0f;

		// Optional scalar parameters
		double metallicValue = 0.0;
		bool bHasMetallic = InParamsPtr->TryGetNumberField(TEXT("metallic"), metallicValue);

		double roughnessValue = 0.5;
		bool bHasRoughness = InParamsPtr->TryGetNumberField(TEXT("roughness"), roughnessValue);

		// Optional parameters
		int32 materialSlot = 0;
		double slotValue;
		if (InParamsPtr->TryGetNumberField(TEXT("material_slot"), slotValue))
		{
			materialSlot = static_cast<int32>(slotValue);
		}

		FString parameterName = TEXT("BaseColor");
		InParamsPtr->TryGetStringField(TEXT("parameter_name"), parameterName);

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript"));
		}

		USCS_Node* targetNode = FWN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName);
		if (!targetNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Cast to PrimitiveComponent
		UPrimitiveComponent* primComponent = Cast<UPrimitiveComponent>(targetNode->ComponentTemplate);
		if (!primComponent)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				TEXT("Component is not a PrimitiveComponent"));
		}

		// Get or create a dynamic material instance
		UMaterialInterface* existingMaterial = primComponent->GetMaterial(materialSlot);

		// Try loading a base material from optional material_path
		FString materialPath;
		if (InParamsPtr->TryGetStringField(TEXT("material_path"), materialPath))
		{
			UMaterialInterface* loadedMat = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(materialPath));
			if (loadedMat)
			{
				existingMaterial = loadedMat;
			}
		}

		// Defensive fallback: verify the material supports all requested parameters.
		// If not, fall back to the generated PBR material (BaseColor + Metallic + Roughness).
		if (existingMaterial)
		{
			bool bNeedsFallback = false;

			// Check vector parameter (BaseColor)
			{
				TArray<FMaterialParameterInfo> paramInfos;
				TArray<FGuid> paramIds;
				existingMaterial->GetAllVectorParameterInfo(paramInfos, paramIds);

				bool bHasVectorParam = false;
				for (const FMaterialParameterInfo& info : paramInfos)
				{
					if (info.Name == FName(*parameterName))
					{
						bHasVectorParam = true;
						break;
					}
				}

				if (!bHasVectorParam)
				{
					bNeedsFallback = true;
				}
			}

			// Check scalar parameters (Metallic / Roughness) if requested
			if (!bNeedsFallback && (bHasMetallic || bHasRoughness))
			{
				TArray<FMaterialParameterInfo> scalarInfos;
				TArray<FGuid> scalarIds;
				existingMaterial->GetAllScalarParameterInfo(scalarInfos, scalarIds);

				auto HasScalarParam = [&scalarInfos](const TCHAR* InName) -> bool
				{
					for (const FMaterialParameterInfo& info : scalarInfos)
					{
						if (info.Name == FName(InName))
						{
							return true;
						}
					}
					return false;
				};

				if (bHasMetallic && !HasScalarParam(TEXT("Metallic")))
				{
					bNeedsFallback = true;
				}
				if (bHasRoughness && !HasScalarParam(TEXT("Roughness")))
				{
					bNeedsFallback = true;
				}
			}

			if (bNeedsFallback)
			{
				UMaterial* fallbackMat = GetOrCreateMCPPBRMaterial();
				if (fallbackMat)
				{
					existingMaterial = fallbackMat;
				}
			}
		}
		else
		{
			// No material at all, use generated PBR material
			existingMaterial = GetOrCreateMCPPBRMaterial();
		}

		if (!existingMaterial)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("No material found at slot %d on component '%s'. Provide 'material_path' with a material that supports the '%s' parameter."), materialSlot, *componentName, *parameterName));
		}

		// Create dynamic material instance and set color
		UMaterialInstanceDynamic* dynMaterial = UMaterialInstanceDynamic::Create(existingMaterial->GetMaterial(), primComponent);
		if (!dynMaterial)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to create dynamic material instance"));
		}
		dynMaterial->SetVectorParameterValue(FName(*parameterName), FLinearColor(r, g, b, a));

		// Set optional scalar parameters
		if (bHasMetallic)
		{
			dynMaterial->SetScalarParameterValue(FName(TEXT("Metallic")), static_cast<float>(metallicValue));
		}
		if (bHasRoughness)
		{
			dynMaterial->SetScalarParameterValue(FName(TEXT("Roughness")), static_cast<float>(roughnessValue));
		}

		primComponent->SetMaterial(materialSlot, dynMaterial);

		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		InResultPtr->SetNumberField(TEXT("material_slot"), materialSlot);
		InResultPtr->SetStringField(TEXT("parameter_name"), parameterName);

		TArray<TSharedPtr<FJsonValue>> colorResult;
		colorResult.Add(MakeShareable(new FJsonValueNumber(r)));
		colorResult.Add(MakeShareable(new FJsonValueNumber(g)));
		colorResult.Add(MakeShareable(new FJsonValueNumber(b)));
		colorResult.Add(MakeShareable(new FJsonValueNumber(a)));
		InResultPtr->SetArrayField(TEXT("color"), colorResult);

		if (bHasMetallic)
		{
			InResultPtr->SetNumberField(TEXT("metallic"), metallicValue);
		}
		if (bHasRoughness)
		{
			InResultPtr->SetNumberField(TEXT("roughness"), roughnessValue);
		}

		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
