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

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("name"), assetName);
		InResultPtr->SetStringField(TEXT("path"), packagePath + assetName);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
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
