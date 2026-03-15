#include "KN_MCP_CommandGroup_BlueprintVariable.h"
#include "KN_MCP_BlueprintUtils.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Engine/Blueprint.h"
#include "EdGraphSchema_K2.h"
#include "Kismet2/BlueprintEditorUtils.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_BlueprintVariable
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_BlueprintVariable);

FKN_MCP_CommandGroup_BlueprintVariable::FKN_MCP_CommandGroup_BlueprintVariable()
{

}

FKN_MCP_CommandGroup_BlueprintVariable::~FKN_MCP_CommandGroup_BlueprintVariable()
{
}

FString FKN_MCP_CommandGroup_BlueprintVariable::GetName() const
{
	return FString("BlueprintVariable");
}

FString FKN_MCP_CommandGroup_BlueprintVariable::GetApplicationName() const
{
	return FString("KN_MCP_EXTENSION");
}

void FKN_MCP_CommandGroup_BlueprintVariable::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_variable_to_blueprint");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "remove_variable_from_blueprint");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_BlueprintVariable::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// add_variable_to_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_variable_to_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->HasField(TEXT("blueprint_name")))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = InParamsPtr->GetStringField(TEXT("blueprint_name"));

		FString variableName;
		if (!InParamsPtr->HasField(TEXT("variable_name")))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_name"));
		}
		variableName = InParamsPtr->GetStringField(TEXT("variable_name"));

		FString variableType;
		if (!InParamsPtr->HasField(TEXT("variable_type")))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_type"));
		}
		variableType = InParamsPtr->GetStringField(TEXT("variable_type"));

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
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
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unsupported variable type: %s. Supported: Bool, Int, Float, String, Name, Text, Vector, Rotator, Transform"), *variableType));
		}

		// Check if variable already exists
		FName varFName(*variableName);
		for (const FBPVariableDescription& existingVar : blueprint->NewVariables)
		{
			if (existingVar.VarName == varFName)
			{
				KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
					*FString::Printf(TEXT("Variable '%s' already exists in blueprint '%s'"), *variableName, *blueprintName));
			}
		}

		// Add the variable
		bool bSuccess = FBlueprintEditorUtils::AddMemberVariable(blueprint, varFName, pinType);
		if (!bSuccess)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to add variable '%s'"), *variableName));
		}

		// Set default value if provided
		FString defaultValue;
		if (InParamsPtr->HasField(TEXT("default_value")))
		{
			defaultValue = InParamsPtr->GetStringField(TEXT("default_value"));
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
		if (InParamsPtr->HasField(TEXT("is_instance_editable")) && InParamsPtr->GetBoolField(TEXT("is_instance_editable")))
		{
			bInstanceEditable = true;
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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// remove_variable_from_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("remove_variable_from_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->HasField(TEXT("blueprint_name")))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}
		blueprintName = InParamsPtr->GetStringField(TEXT("blueprint_name"));

		FString variableName;
		if (!InParamsPtr->HasField(TEXT("variable_name")))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_name"));
		}
		variableName = InParamsPtr->GetStringField(TEXT("variable_name"));

		// Find blueprint
		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
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
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Variable '%s' not found in blueprint '%s'"), *variableName, *blueprintName));
		}

		// Remove the variable
		FBlueprintEditorUtils::RemoveMemberVariable(blueprint, varFName);
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("variable_name"), variableName);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
