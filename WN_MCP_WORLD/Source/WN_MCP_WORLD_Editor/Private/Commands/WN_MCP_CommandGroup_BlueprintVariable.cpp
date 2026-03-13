#include "WN_MCP_CommandGroup_BlueprintVariable.h"
#include "WN_MCP_BlueprintUtils.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Engine/Blueprint.h"
#include "EdGraphSchema_K2.h"
#include "Kismet2/BlueprintEditorUtils.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_BlueprintVariable
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_BlueprintVariable);

FWN_MCP_CommandGroup_BlueprintVariable::FWN_MCP_CommandGroup_BlueprintVariable()
{

}

FWN_MCP_CommandGroup_BlueprintVariable::~FWN_MCP_CommandGroup_BlueprintVariable()
{
}

FString FWN_MCP_CommandGroup_BlueprintVariable::GetName() const
{
	return FString("BlueprintVariable");
}

FString FWN_MCP_CommandGroup_BlueprintVariable::GetApplicationName() const
{
	return FString("WN_MCP_WORLD");
}

void FWN_MCP_CommandGroup_BlueprintVariable::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_variable_to_blueprint");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "remove_variable_from_blueprint");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_BlueprintVariable::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// add_variable_to_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_variable_to_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString variableName;
		if (!InParamsPtr->TryGetStringField(TEXT("variable_name"), variableName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_name"));
		}

		FString variableType;
		if (!InParamsPtr->TryGetStringField(TEXT("variable_type"), variableType))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_type"));
		}

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Map variable_type string to FEdGraphPinType
		FEdGraphPinType pinType;

		if (variableType == TEXT("Bool"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
		}
		else if (variableType == TEXT("Int"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Int;
		}
		else if (variableType == TEXT("Float"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Real;
			pinType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
		}
		else if (variableType == TEXT("String"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_String;
		}
		else if (variableType == TEXT("Name"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Name;
		}
		else if (variableType == TEXT("Text"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Text;
		}
		else if (variableType == TEXT("Vector"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			pinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
		}
		else if (variableType == TEXT("Rotator"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			pinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
		}
		else if (variableType == TEXT("Transform"))
		{
			pinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
			pinType.PinSubCategoryObject = TBaseStructure<FTransform>::Get();
		}
		else
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unsupported variable type: %s. Supported: Bool, Int, Float, String, Name, Text, Vector, Rotator, Transform"), *variableType));
		}

		// Check if variable already exists
		FName varFName(*variableName);
		for (const FBPVariableDescription& existingVar : blueprint->NewVariables)
		{
			if (existingVar.VarName == varFName)
			{
				WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
					*FString::Printf(TEXT("Variable '%s' already exists in blueprint '%s'"), *variableName, *blueprintName));
			}
		}

		// Add the variable
		bool bSuccess = FBlueprintEditorUtils::AddMemberVariable(blueprint, varFName, pinType);
		if (!bSuccess)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to add variable '%s'"), *variableName));
		}

		// Set default value if provided
		FString defaultValue;
		if (InParamsPtr->TryGetStringField(TEXT("default_value"), defaultValue))
		{
			for (FBPVariableDescription& varDesc : blueprint->NewVariables)
			{
				if (varDesc.VarName == varFName)
				{
					varDesc.DefaultValue = defaultValue;
					break;
				}
			}
		}

		// Set instance editable if specified
		bool bInstanceEditable = false;
		if (InParamsPtr->TryGetBoolField(TEXT("is_instance_editable"), bInstanceEditable) && bInstanceEditable)
		{
			for (FBPVariableDescription& varDesc : blueprint->NewVariables)
			{
				if (varDesc.VarName == varFName)
				{
					varDesc.PropertyFlags |= CPF_Edit;
					break;
				}
			}
		}

		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("variable_name"), variableName);
		InResultPtr->SetStringField(TEXT("variable_type"), variableType);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// remove_variable_from_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("remove_variable_from_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString variableName;
		if (!InParamsPtr->TryGetStringField(TEXT("variable_name"), variableName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_name"));
		}

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Check if variable exists
		FName varFName(*variableName);
		bool bFound = false;
		for (const FBPVariableDescription& existingVar : blueprint->NewVariables)
		{
			if (existingVar.VarName == varFName)
			{
				bFound = true;
				break;
			}
		}

		if (!bFound)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Variable '%s' not found in blueprint '%s'"), *variableName, *blueprintName));
		}

		// Remove the variable
		FBlueprintEditorUtils::RemoveMemberVariable(blueprint, varFName);
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("variable_name"), variableName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
