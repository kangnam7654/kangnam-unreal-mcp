#include "KN_MCP_CommandGroup_Property.h"
#include "KN_MCP_BlueprintUtils.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Engine/Blueprint.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "EditorAssetLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_Property
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_Property);

FKN_MCP_CommandGroup_Property::FKN_MCP_CommandGroup_Property()
{

}

FKN_MCP_CommandGroup_Property::~FKN_MCP_CommandGroup_Property()
{
}

FString FKN_MCP_CommandGroup_Property::GetName() const
{
	return FString("Property");
}

FString FKN_MCP_CommandGroup_Property::GetApplicationName() const
{
	return FString("KN_MCP_EXTENSION");
}

void FKN_MCP_CommandGroup_Property::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "set_static_mesh_properties");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "set_physics_properties");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_Property::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// set_static_mesh_properties
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("set_static_mesh_properties")))
	{
		FString blueprintName;
		const FString* _blueprintNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("blueprint_name")) : nullptr;
		if (!_blueprintNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = *_blueprintNamePtr;

		FString componentName;
		const FString* _componentNamePtr = InParamsPtr->TryGetStringField(TEXT("component_name"));
		if (!_componentNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}
		componentName = *_componentNamePtr;

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript (not an Actor-based Blueprint?)"));
		}

		USCS_Node* targetNode = FKN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName);
		if (!targetNode)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Cast to StaticMeshComponent
		UStaticMeshComponent* meshComponent = Cast<UStaticMeshComponent>(targetNode->ComponentTemplate);
		if (!meshComponent)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				TEXT("Component is not a StaticMeshComponent"));
		}

		// Set static mesh if provided
		FString meshPath;
		if (const FString* _meshPathPtr = InParamsPtr->TryGetStringField(TEXT("static_mesh")))
		{
			meshPath = *_meshPathPtr;
			UStaticMesh* mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(meshPath));
			if (mesh)
			{
				meshComponent->SetStaticMesh(mesh);
			}
			else
			{
				KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Static mesh not found: %s"), *meshPath));
			}
		}

		// Set material if provided
		FString materialPath;
		if (const FString* _materialPathPtr = InParamsPtr->TryGetStringField(TEXT("material")))
		{
			materialPath = *_materialPathPtr;
			UMaterialInterface* material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(materialPath));
			if (material)
			{
				meshComponent->SetMaterial(0, material);
			}
			else
			{
				KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Material not found: %s"), *materialPath));
			}
		}

		// Mark blueprint as modified
		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// set_physics_properties
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("set_physics_properties")))
	{
		FString blueprintName;
		const FString* _blueprintNamePtr = InParamsPtr.IsValid() ? InParamsPtr->TryGetStringField(TEXT("blueprint_name")) : nullptr;
		if (!_blueprintNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = *_blueprintNamePtr;

		FString componentName;
		const FString* _componentNamePtr = InParamsPtr->TryGetStringField(TEXT("component_name"));
		if (!_componentNamePtr)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: component_name"));
		}
		componentName = *_componentNamePtr;

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		if (!blueprint->SimpleConstructionScript)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				TEXT("Blueprint has no SimpleConstructionScript (not an Actor-based Blueprint?)"));
		}

		USCS_Node* targetNode = FKN_MCP_BlueprintUtils::FindSCSNodeByName(blueprint, componentName);
		if (!targetNode)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Component not found: %s"), *componentName));
		}

		// Cast to PrimitiveComponent
		UPrimitiveComponent* primComponent = Cast<UPrimitiveComponent>(targetNode->ComponentTemplate);
		if (!primComponent)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				TEXT("Component is not a PrimitiveComponent (physics requires a PrimitiveComponent)"));
		}

		// Set physics properties
		bool bValue;
		if (const bool* _bValuePtr = InParamsPtr->TryGetBoolField(TEXT("simulate_physics")))
		{
			bValue = *_bValuePtr;
			primComponent->SetSimulatePhysics(bValue);
		}

		double massValue;
		if (const double* _massValuePtr = InParamsPtr->TryGetNumberField(TEXT("mass")))
		{
			massValue = *_massValuePtr;
			primComponent->SetMassOverrideInKg(NAME_None, static_cast<float>(massValue));
		}

		double linearDamping;
		if (const double* _linearDampingPtr = InParamsPtr->TryGetNumberField(TEXT("linear_damping")))
		{
			linearDamping = *_linearDampingPtr;
			primComponent->SetLinearDamping(static_cast<float>(linearDamping));
		}

		double angularDamping;
		if (const double* _angularDampingPtr = InParamsPtr->TryGetNumberField(TEXT("angular_damping")))
		{
			angularDamping = *_angularDampingPtr;
			primComponent->SetAngularDamping(static_cast<float>(angularDamping));
		}

		// Mark blueprint as modified
		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
