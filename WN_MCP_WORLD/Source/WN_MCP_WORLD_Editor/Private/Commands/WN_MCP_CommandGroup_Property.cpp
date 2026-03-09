#include "WN_MCP_CommandGroup_Property.h"
#include "WN_MCP_BlueprintUtils.h"
#include "WN_MCP_Module.h"

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
// FWN_MCP_CommandGroup_Property
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Property);

FWN_MCP_CommandGroup_Property::FWN_MCP_CommandGroup_Property()
{

}

FWN_MCP_CommandGroup_Property::~FWN_MCP_CommandGroup_Property()
{

}

FString FWN_MCP_CommandGroup_Property::GetName() const
{
	return FString("Property");
}

void FWN_MCP_CommandGroup_Property::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("set_static_mesh_properties")));
	InOutCommandNames.Add(FString(TEXT("set_physics_properties")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Property::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// set_static_mesh_properties
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("set_static_mesh_properties")))
	{
		// Get required parameters
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
				TEXT("Blueprint has no SimpleConstructionScript (not an Actor-based Blueprint?)"));
		}

		// Find the target SCS node
		USCS_Node* targetNode = nullptr;
		for (USCS_Node* node : blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (node && node->GetVariableName().ToString() == componentName)
			{
				targetNode = node;
				break;
			}
		}

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

		// Set static mesh if provided
		FString meshPath;
		if (InParamsPtr->TryGetStringField(TEXT("static_mesh"), meshPath))
		{
			UStaticMesh* mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(meshPath));
			if (mesh)
			{
				meshComponent->SetStaticMesh(mesh);
			}
			else
			{
				WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Static mesh not found: %s"), *meshPath));
			}
		}

		// Set material if provided
		FString materialPath;
		if (InParamsPtr->TryGetStringField(TEXT("material"), materialPath))
		{
			UMaterialInterface* material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(materialPath));
			if (material)
			{
				meshComponent->SetMaterial(0, material);
			}
			else
			{
				WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Material not found: %s"), *materialPath));
			}
		}

		// Mark blueprint as modified
		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// set_physics_properties
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("set_physics_properties")))
	{
		// Get required parameters
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
				TEXT("Blueprint has no SimpleConstructionScript (not an Actor-based Blueprint?)"));
		}

		// Find the target SCS node
		USCS_Node* targetNode = nullptr;
		for (USCS_Node* node : blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (node && node->GetVariableName().ToString() == componentName)
			{
				targetNode = node;
				break;
			}
		}

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
				TEXT("Component is not a PrimitiveComponent (physics requires a PrimitiveComponent)"));
		}

		// Set physics properties
		bool bValue;
		if (InParamsPtr->TryGetBoolField(TEXT("simulate_physics"), bValue))
		{
			primComponent->SetSimulatePhysics(bValue);
		}

		double massValue;
		if (InParamsPtr->TryGetNumberField(TEXT("mass"), massValue))
		{
			primComponent->SetMassOverrideInKg(NAME_None, static_cast<float>(massValue));
		}

		double linearDamping;
		if (InParamsPtr->TryGetNumberField(TEXT("linear_damping"), linearDamping))
		{
			primComponent->SetLinearDamping(static_cast<float>(linearDamping));
		}

		double angularDamping;
		if (InParamsPtr->TryGetNumberField(TEXT("angular_damping"), angularDamping))
		{
			primComponent->SetAngularDamping(static_cast<float>(angularDamping));
		}

		// Mark blueprint as modified
		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		// Return result
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("component_name"), componentName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
