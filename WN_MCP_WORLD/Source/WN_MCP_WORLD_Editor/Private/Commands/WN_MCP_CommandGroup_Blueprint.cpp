#include "WN_MCP_CommandGroup_Blueprint.h"
#include "WN_MCP_BlueprintUtils.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "Factories/BlueprintFactory.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
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

FString FWN_MCP_CommandGroup_Blueprint::GetApplicationName() const
{
	return FString("WN_MCP_WORLD");
}

void FWN_MCP_CommandGroup_Blueprint::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "create_blueprint", "Create a new Blueprint asset");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "read_blueprint_content", "Read Blueprint content and properties");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "compile_blueprint", "Compile a Blueprint");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "delete_blueprint", "Delete a Blueprint asset");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_blueprints", "Get all Blueprint assets");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "find_blueprints_by_name", "Find Blueprints by name pattern");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "spawn_blueprint_actor", "Spawn an actor from a Blueprint");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_Blueprint::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// create_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("create_blueprint")))
	{
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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("name"), assetName);
		InResultPtr->SetStringField(TEXT("path"), packagePath + assetName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// read_blueprint_content
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("read_blueprint_content")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
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

		// Find the blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("parent_class"), blueprint->ParentClass ? blueprint->ParentClass->GetName() : TEXT("None"));

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
			InResultPtr->SetArrayField(TEXT("variables"), variableArray);
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
			InResultPtr->SetArrayField(TEXT("functions"), functionArray);
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

			InResultPtr->SetObjectField(TEXT("event_graph"), eventGraphObj);
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
			InResultPtr->SetArrayField(TEXT("interfaces"), interfaceArray);
		}

		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// compile_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("compile_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		// Find the blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Compile the blueprint
		FKismetEditorUtilities::CompileBlueprint(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("name"), blueprintName);
		InResultPtr->SetBoolField(TEXT("compiled"), true);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// delete_blueprint
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("delete_blueprint")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		// Find the blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Get the asset path for deletion
		FString blueprintPath = blueprint->GetPathName();
		// Remove object name suffix (e.g. "/Game/Blueprints/MyBP.MyBP" -> "/Game/Blueprints/MyBP")
		FString packagePath = FPackageName::ObjectPathToPackageName(blueprintPath);

		// Check for referencers unless force is true
		bool bForce = false;
		InParamsPtr->TryGetBoolField(TEXT("force"), bForce);

		if (!bForce)
		{
			TArray<FName> referencers;
			FAssetRegistryModule& assetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
			assetRegistryModule.Get().GetReferencers(FName(*packagePath), referencers);

			if (referencers.Num() > 0)
			{
				TArray<TSharedPtr<FJsonValue>> refArray;
				for (const FName& ref : referencers)
				{
					refArray.Add(MakeShareable(new FJsonValueString(ref.ToString())));
				}

				TSharedPtr<FJsonObject> errorData = MakeShareable(new FJsonObject());
				errorData->SetStringField(TEXT("message"), FString::Printf(TEXT("Blueprint '%s' is referenced by %d asset(s). Use force=true to delete anyway."), *blueprintName, referencers.Num()));
				errorData->SetArrayField(TEXT("referencers"), refArray);
				WN_RETURN_COMMAND_ERROR_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, errorData);
			}
		}

		// Delete the asset
		if (!UEditorAssetLibrary::DeleteAsset(packagePath))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to delete blueprint: %s"), *blueprintName));
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("deleted_path"), packagePath);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// get_blueprints
	//-------------------------------------------------------------------------

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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), blueprintArray.Num());
		InResultPtr->SetArrayField(TEXT("blueprints"), blueprintArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// find_blueprints_by_name
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("find_blueprints_by_name")))
	{
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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetNumberField(TEXT("count"), blueprintArray.Num());
		InResultPtr->SetArrayField(TEXT("blueprints"), blueprintArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// spawn_blueprint_actor
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("spawn_blueprint_actor")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString actorName;
		if (!InParamsPtr->TryGetStringField(TEXT("name"), actorName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: name"));
		}

		// Find blueprint
		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		// Verify GeneratedClass exists
		if (!blueprint->GeneratedClass)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint '%s' has no GeneratedClass. Compile the Blueprint first."), *blueprintName));
		}

		// Check for duplicate actor name
		TArray<AActor*> allActors;
		UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);
		for (AActor* actor : allActors)
		{
			if (actor && actor->GetName() == actorName)
			{
				WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
					*FString::Printf(TEXT("Actor with name '%s' already exists"), *actorName));
			}
		}

		// Optional transform parameters
		FVector location(0.0f, 0.0f, 0.0f);
		FRotator rotation(0.0f, 0.0f, 0.0f);
		FVector scale(1.0f, 1.0f, 1.0f);

		if (InParamsPtr->HasField(TEXT("location")))
		{
			const TArray<TSharedPtr<FJsonValue>>* locationArray;
			if (InParamsPtr->TryGetArrayField(TEXT("location"), locationArray) && locationArray->Num() >= 3)
			{
				location.X = (*locationArray)[0]->AsNumber();
				location.Y = (*locationArray)[1]->AsNumber();
				location.Z = (*locationArray)[2]->AsNumber();
			}
		}

		if (InParamsPtr->HasField(TEXT("rotation")))
		{
			const TArray<TSharedPtr<FJsonValue>>* rotationArray;
			if (InParamsPtr->TryGetArrayField(TEXT("rotation"), rotationArray) && rotationArray->Num() >= 3)
			{
				rotation.Pitch = (*rotationArray)[0]->AsNumber();
				rotation.Yaw = (*rotationArray)[1]->AsNumber();
				rotation.Roll = (*rotationArray)[2]->AsNumber();
			}
		}

		if (InParamsPtr->HasField(TEXT("scale")))
		{
			const TArray<TSharedPtr<FJsonValue>>* scaleArray;
			if (InParamsPtr->TryGetArrayField(TEXT("scale"), scaleArray) && scaleArray->Num() >= 3)
			{
				scale.X = (*scaleArray)[0]->AsNumber();
				scale.Y = (*scaleArray)[1]->AsNumber();
				scale.Z = (*scaleArray)[2]->AsNumber();
			}
		}

		// Spawn the actor from Blueprint's GeneratedClass
		FActorSpawnParameters spawnParams;
		spawnParams.Name = *actorName;

		AActor* newActor = GWorld->SpawnActor<AActor>(blueprint->GeneratedClass, location, rotation, spawnParams);
		if (!newActor)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to spawn actor from Blueprint '%s'"), *blueprintName));
		}

		// Apply scale
		newActor->SetActorScale3D(scale);

		// Build actor JSON
		TSharedPtr<FJsonObject> actorObject = MakeShareable(new FJsonObject());
		actorObject->SetStringField(TEXT("name"), newActor->GetName());
		actorObject->SetStringField(TEXT("class"), newActor->GetClass()->GetName());

		FVector actorLocation = newActor->GetActorLocation();
		TArray<TSharedPtr<FJsonValue>> locationJsonArray;
		locationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorLocation.X)));
		locationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorLocation.Y)));
		locationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorLocation.Z)));
		actorObject->SetArrayField(TEXT("location"), locationJsonArray);

		FRotator actorRotation = newActor->GetActorRotation();
		TArray<TSharedPtr<FJsonValue>> rotationJsonArray;
		rotationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorRotation.Pitch)));
		rotationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorRotation.Yaw)));
		rotationJsonArray.Add(MakeShareable(new FJsonValueNumber(actorRotation.Roll)));
		actorObject->SetArrayField(TEXT("rotation"), rotationJsonArray);

		FVector actorScale = newActor->GetActorScale3D();
		TArray<TSharedPtr<FJsonValue>> scaleJsonArray;
		scaleJsonArray.Add(MakeShareable(new FJsonValueNumber(actorScale.X)));
		scaleJsonArray.Add(MakeShareable(new FJsonValueNumber(actorScale.Y)));
		scaleJsonArray.Add(MakeShareable(new FJsonValueNumber(actorScale.Z)));
		actorObject->SetArrayField(TEXT("scale"), scaleJsonArray);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetObjectField(TEXT("actor"), actorObject);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
