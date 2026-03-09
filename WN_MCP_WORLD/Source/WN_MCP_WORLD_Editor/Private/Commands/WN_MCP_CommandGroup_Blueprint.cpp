#include "WN_MCP_CommandGroup_Blueprint.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "Factories/BlueprintFactory.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "Kismet2/KismetEditorUtilities.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_Blueprint
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Blueprint);

FWN_MCP_CommandGroup_Blueprint::FWN_MCP_CommandGroup_Blueprint()
{

}

FWN_MCP_CommandGroup_Blueprint::~FWN_MCP_CommandGroup_Blueprint()
{

}

FString FWN_MCP_CommandGroup_Blueprint::GetName() const
{
	return FString("Blueprint");
}

void FWN_MCP_CommandGroup_Blueprint::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("create_blueprint")));
	InOutCommandNames.Add(FString(TEXT("read_blueprint_content")));
	InOutCommandNames.Add(FString(TEXT("compile_blueprint")));
	InOutCommandNames.Add(FString(TEXT("delete_blueprint")));
	InOutCommandNames.Add(FString(TEXT("get_blueprints")));
	InOutCommandNames.Add(FString(TEXT("find_blueprints_by_name")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Blueprint::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	if (InCommandName == FString(TEXT("create_blueprint")))
	{
		// Get required parameters
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		// Check if blueprint already exists
		FString packagePath = TEXT("/Game/Blueprints/");
		FString assetName = blueprintName;
		if (UEditorAssetLibrary::DoesAssetExist(packagePath + assetName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint already exists: %s"), *blueprintName));
		}

		// Create the blueprint factory
		UBlueprintFactory* factory = NewObject<UBlueprintFactory>();

		// Handle parent class
		FString parentClassName;
		InParamsPtr->TryGetStringField(TEXT("parent_class"), parentClassName);

		// Default to Actor if no parent class specified
		UClass* selectedParentClass = AActor::StaticClass();

		if (!parentClassName.IsEmpty())
		{
			FString className = parentClassName;
			if (!className.StartsWith(TEXT("A")))
			{
				className = TEXT("A") + className;
			}

			// Try direct StaticClass lookup for common classes
			UClass* foundClass = nullptr;
			if (className == TEXT("APawn"))
			{
				foundClass = APawn::StaticClass();
			}
			else if (className == TEXT("AActor"))
			{
				foundClass = AActor::StaticClass();
			}
			else
			{
				// Try loading the class
				const FString classPath = FString::Printf(TEXT("/Script/Engine.%s"), *className);
				foundClass = LoadClass<AActor>(nullptr, *classPath);

				if (!foundClass)
				{
					const FString gameClassPath = FString::Printf(TEXT("/Script/Game.%s"), *className);
					foundClass = LoadClass<AActor>(nullptr, *gameClassPath);
				}
			}

			if (foundClass)
			{
				selectedParentClass = foundClass;
			}
		}

		factory->ParentClass = selectedParentClass;

		// Create the blueprint
		UPackage* package = CreatePackage(*(packagePath + assetName));
		UBlueprint* newBlueprint = Cast<UBlueprint>(factory->FactoryCreateNew(
			UBlueprint::StaticClass(), package, *assetName, RF_Standalone | RF_Public, nullptr, GWarn));

		if (!newBlueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("Failed to create blueprint"));
		}

		// Notify the asset registry
		FAssetRegistryModule::AssetCreated(newBlueprint);

		// Mark the package dirty
		package->MarkPackageDirty();

		TSharedPtr<FJsonObject> ResultPtr = MakeShareable(new FJsonObject());
		ResultPtr->SetStringField(TEXT("name"), assetName);
		ResultPtr->SetStringField(TEXT("path"), packagePath + assetName);
		WN_RETURN_COMMAND_RESPONSE(ResultPtr);
	}

	if (InCommandName == FString(TEXT("read_blueprint_content")))
	{
		// Get required parameters
		FString blueprintPath;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_path"), blueprintPath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_path"));
		}

		// Get optional filter flags
		bool bIncludeEventGraph = true;
		bool bIncludeFunctions = true;
		bool bIncludeVariables = true;
		bool bIncludeInterfaces = true;

		InParamsPtr->TryGetBoolField(TEXT("include_event_graph"), bIncludeEventGraph);
		InParamsPtr->TryGetBoolField(TEXT("include_functions"), bIncludeFunctions);
		InParamsPtr->TryGetBoolField(TEXT("include_variables"), bIncludeVariables);
		InParamsPtr->TryGetBoolField(TEXT("include_interfaces"), bIncludeInterfaces);

		// Load the blueprint
		UBlueprint* blueprint = Cast<UBlueprint>(UEditorAssetLibrary::LoadAsset(blueprintPath));
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to load blueprint: %s"), *blueprintPath));
		}

		TSharedPtr<FJsonObject> ResultPtr = MakeShareable(new FJsonObject());
		ResultPtr->SetStringField(TEXT("blueprint_path"), blueprintPath);
		ResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		ResultPtr->SetStringField(TEXT("parent_class"), blueprint->ParentClass ? blueprint->ParentClass->GetName() : TEXT("None"));

		// Variables
		if (bIncludeVariables)
		{
			TArray<TSharedPtr<FJsonValue>> variableArray;
			for (const FBPVariableDescription& variable : blueprint->NewVariables)
			{
				TSharedPtr<FJsonObject> varObj = MakeShareable(new FJsonObject());
				varObj->SetStringField(TEXT("name"), variable.VarName.ToString());
				varObj->SetStringField(TEXT("type"), variable.VarType.PinCategory.ToString());
				varObj->SetStringField(TEXT("default_value"), variable.DefaultValue);
				varObj->SetBoolField(TEXT("is_editable"), (variable.PropertyFlags & CPF_Edit) != 0);
				variableArray.Add(MakeShareable(new FJsonValueObject(varObj)));
			}
			ResultPtr->SetArrayField(TEXT("variables"), variableArray);
		}

		// Functions
		if (bIncludeFunctions)
		{
			TArray<TSharedPtr<FJsonValue>> functionArray;
			for (UEdGraph* graph : blueprint->FunctionGraphs)
			{
				if (graph)
				{
					TSharedPtr<FJsonObject> funcObj = MakeShareable(new FJsonObject());
					funcObj->SetStringField(TEXT("name"), graph->GetName());
					funcObj->SetStringField(TEXT("graph_type"), TEXT("Function"));
					funcObj->SetNumberField(TEXT("node_count"), graph->Nodes.Num());
					functionArray.Add(MakeShareable(new FJsonValueObject(funcObj)));
				}
			}
			ResultPtr->SetArrayField(TEXT("functions"), functionArray);
		}

		// Event graph
		if (bIncludeEventGraph)
		{
			TSharedPtr<FJsonObject> eventGraphObj = MakeShareable(new FJsonObject());

			for (UEdGraph* graph : blueprint->UbergraphPages)
			{
				if (graph && graph->GetName() == TEXT("EventGraph"))
				{
					eventGraphObj->SetStringField(TEXT("name"), graph->GetName());
					eventGraphObj->SetNumberField(TEXT("node_count"), graph->Nodes.Num());

					TArray<TSharedPtr<FJsonValue>> nodeArray;
					for (UEdGraphNode* node : graph->Nodes)
					{
						if (node)
						{
							TSharedPtr<FJsonObject> nodeObj = MakeShareable(new FJsonObject());
							nodeObj->SetStringField(TEXT("name"), node->GetName());
							nodeObj->SetStringField(TEXT("class"), node->GetClass()->GetName());
							nodeArray.Add(MakeShareable(new FJsonValueObject(nodeObj)));
						}
					}
					eventGraphObj->SetArrayField(TEXT("nodes"), nodeArray);
					break;
				}
			}

			ResultPtr->SetObjectField(TEXT("event_graph"), eventGraphObj);
		}

		// Interfaces
		if (bIncludeInterfaces)
		{
			TArray<TSharedPtr<FJsonValue>> interfaceArray;
			for (const FBPInterfaceDescription& bpInterface : blueprint->ImplementedInterfaces)
			{
				TSharedPtr<FJsonObject> interfaceObj = MakeShareable(new FJsonObject());
				interfaceObj->SetStringField(TEXT("name"), bpInterface.Interface ? bpInterface.Interface->GetName() : TEXT("Unknown"));
				interfaceArray.Add(MakeShareable(new FJsonValueObject(interfaceObj)));
			}
			ResultPtr->SetArrayField(TEXT("interfaces"), interfaceArray);
		}

		WN_RETURN_COMMAND_RESPONSE(ResultPtr);
	}

	if (InCommandName == FString(TEXT("compile_blueprint")))
	{
		// Get required parameters
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		// Find the blueprint
		UBlueprint* blueprint = FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Compile the blueprint
		FKismetEditorUtilities::CompileBlueprint(blueprint);

		TSharedPtr<FJsonObject> ResultPtr = MakeShareable(new FJsonObject());
		ResultPtr->SetStringField(TEXT("name"), blueprintName);
		ResultPtr->SetBoolField(TEXT("compiled"), true);
		WN_RETURN_COMMAND_RESPONSE(ResultPtr);
	}

	if (InCommandName == FString(TEXT("delete_blueprint")))
	{
		// Get required parameters
		FString blueprintPath;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_path"), blueprintPath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_path"));
		}

		// Check if asset exists
		if (!UEditorAssetLibrary::DoesAssetExist(blueprintPath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintPath));
		}

		// Check for referencers unless force is true
		bool bForce = false;
		InParamsPtr->TryGetBoolField(TEXT("force"), bForce);

		if (!bForce)
		{
			TArray<FName> referencers;
			FString assetName = FPaths::GetBaseFilename(blueprintPath);
			FString objectPath = FString::Printf(TEXT("%s.%s"), *blueprintPath, *assetName);
			FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
			assetRegistryModule.Get().GetReferencers(FName(*objectPath), referencers);

			if (referencers.Num() > 0)
			{
				TArray<TSharedPtr<FJsonValue>> refArray;
				for (const FName& ref : referencers)
				{
					refArray.Add(MakeShareable(new FJsonValueString(ref.ToString())));
				}

				TSharedPtr<FJsonObject> errorData = MakeShareable(new FJsonObject());
				errorData->SetStringField(TEXT("message"), FString::Printf(TEXT("Blueprint '%s' is referenced by %d asset(s). Use force=true to delete anyway."), *blueprintPath, referencers.Num()));
				errorData->SetArrayField(TEXT("referencers"), refArray);
				WN_RETURN_COMMAND_ERROR_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, errorData);
			}
		}

		// Delete the asset
		if (!UEditorAssetLibrary::DeleteAsset(blueprintPath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to delete blueprint: %s"), *blueprintPath));
		}

		TSharedPtr<FJsonObject> ResultPtr = MakeShareable(new FJsonObject());
		ResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		ResultPtr->SetStringField(TEXT("deleted_path"), blueprintPath);
		WN_RETURN_COMMAND_RESPONSE(ResultPtr);
	}

	if (InCommandName == FString(TEXT("get_blueprints")))
	{
		// Optional search path (default: /Game/)
		FString searchPath = TEXT("/Game/");
		if (InParamsPtr.IsValid())
		{
			InParamsPtr->TryGetStringField(TEXT("search_path"), searchPath);
		}

		// Query asset registry for all Blueprint assets
		FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));

		FARFilter filter;
		filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
		filter.PackagePaths.Add(FName(*searchPath));
		filter.bRecursivePaths = true;

		TArray<FAssetData> assetList;
		assetRegistryModule.Get().GetAssets(filter, assetList);

		TArray<TSharedPtr<FJsonValue>> blueprintArray;
		for (const FAssetData& assetData : assetList)
		{
			TSharedPtr<FJsonObject> bpObj = MakeShareable(new FJsonObject());
			bpObj->SetStringField(TEXT("name"), assetData.AssetName.ToString());
			bpObj->SetStringField(TEXT("path"), assetData.GetObjectPathString());
			bpObj->SetStringField(TEXT("package_path"), assetData.PackagePath.ToString());
			blueprintArray.Add(MakeShareable(new FJsonValueObject(bpObj)));
		}

		TSharedPtr<FJsonObject> ResultPtr = MakeShareable(new FJsonObject());
		ResultPtr->SetNumberField(TEXT("count"), blueprintArray.Num());
		ResultPtr->SetArrayField(TEXT("blueprints"), blueprintArray);
		WN_RETURN_COMMAND_RESPONSE(ResultPtr);
	}

	if (InCommandName == FString(TEXT("find_blueprints_by_name")))
	{
		// Get required parameters
		FString searchText;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("search_text"), searchText))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: search_text"));
		}

		// Query asset registry for all Blueprint assets
		FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));

		FARFilter filter;
		filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
		filter.PackagePaths.Add(FName(TEXT("/Game/")));
		filter.bRecursivePaths = true;

		TArray<FAssetData> assetList;
		assetRegistryModule.Get().GetAssets(filter, assetList);

		TArray<TSharedPtr<FJsonValue>> blueprintArray;
		for (const FAssetData& assetData : assetList)
		{
			if (assetData.AssetName.ToString().Contains(searchText))
			{
				TSharedPtr<FJsonObject> bpObj = MakeShareable(new FJsonObject());
				bpObj->SetStringField(TEXT("name"), assetData.AssetName.ToString());
				bpObj->SetStringField(TEXT("path"), assetData.GetObjectPathString());
				bpObj->SetStringField(TEXT("package_path"), assetData.PackagePath.ToString());
				blueprintArray.Add(MakeShareable(new FJsonValueObject(bpObj)));
			}
		}

		TSharedPtr<FJsonObject> ResultPtr = MakeShareable(new FJsonObject());
		ResultPtr->SetNumberField(TEXT("count"), blueprintArray.Num());
		ResultPtr->SetArrayField(TEXT("blueprints"), blueprintArray);
		WN_RETURN_COMMAND_RESPONSE(ResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}

UBlueprint* FWN_MCP_CommandGroup_Blueprint::FindBlueprintByName(const FString& InBlueprintName)
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
