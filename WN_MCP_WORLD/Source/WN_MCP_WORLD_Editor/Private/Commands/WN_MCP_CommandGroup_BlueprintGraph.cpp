#include "WN_MCP_CommandGroup_BlueprintGraph.h"
#include "WN_MCP_BlueprintUtils.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Blueprint.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "GameFramework/Actor.h"

//-----------------------------------------------------------------------------
// Helper: Find EventGraph
//-----------------------------------------------------------------------------

static UEdGraph* FindEventGraph(UBlueprint* InBlueprint)
{
	for (UEdGraph* graph : InBlueprint->UbergraphPages)
	{
		if (graph && graph->GetName() == TEXT("EventGraph"))
		{
			return graph;
		}
	}
	return nullptr;
}

//-----------------------------------------------------------------------------
// Helper: Find node by GUID string
//-----------------------------------------------------------------------------

static UEdGraphNode* FindNodeByGuid(UEdGraph* InGraph, const FString& InGuidString)
{
	FGuid targetGuid;
	if (!FGuid::Parse(InGuidString, targetGuid))
	{
		return nullptr;
	}

	for (UEdGraphNode* node : InGraph->Nodes)
	{
		if (node && node->NodeGuid == targetGuid)
		{
			return node;
		}
	}
	return nullptr;
}

//-----------------------------------------------------------------------------
// Helper: Build pin info JSON
//-----------------------------------------------------------------------------

static TSharedPtr<FJsonObject> BuildPinInfo(const UEdGraphPin* InPin)
{
	TSharedPtr<FJsonObject> pinObj = MakeShareable(new FJsonObject());
	pinObj->SetStringField(TEXT("pin_name"), InPin->PinName.ToString());
	pinObj->SetStringField(TEXT("pin_type"), InPin->PinType.PinCategory.ToString());
	pinObj->SetStringField(TEXT("direction"), InPin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
	return pinObj;
}

//-----------------------------------------------------------------------------
// Helper: Build pins array for a node
//-----------------------------------------------------------------------------

static TArray<TSharedPtr<FJsonValue>> BuildPinsArray(const UEdGraphNode* InNode)
{
	TArray<TSharedPtr<FJsonValue>> pinsArray;
	for (const UEdGraphPin* pin : InNode->Pins)
	{
		if (pin && !pin->bHidden)
		{
			pinsArray.Add(MakeShareable(new FJsonValueObject(BuildPinInfo(pin))));
		}
	}
	return pinsArray;
}

//-----------------------------------------------------------------------------
// Helper: Find UFunction by name in common classes
//-----------------------------------------------------------------------------

static UFunction* FindFunctionByName(const FString& InFunctionName, const FString& InTargetClass, UBlueprint* InBlueprint)
{
	// If target class specified, search there first
	if (!InTargetClass.IsEmpty())
	{
		UClass* targetClass = FindObject<UClass>(nullptr, *InTargetClass);
		if (targetClass)
		{
			UFunction* func = targetClass->FindFunctionByName(FName(*InFunctionName));
			if (func)
			{
				return func;
			}
		}
	}

	// Search in blueprint's parent class hierarchy
	if (InBlueprint->ParentClass)
	{
		UFunction* func = InBlueprint->ParentClass->FindFunctionByName(FName(*InFunctionName));
		if (func)
		{
			return func;
		}
	}

	// Search common library classes
	static const UClass* commonClasses[] = {
		UKismetSystemLibrary::StaticClass(),
		UKismetMathLibrary::StaticClass(),
		UGameplayStatics::StaticClass(),
	};

	for (const UClass* cls : commonClasses)
	{
		UFunction* func = cls->FindFunctionByName(FName(*InFunctionName));
		if (func)
		{
			return func;
		}
	}

	return nullptr;
}

//-----------------------------------------------------------------------------
// Helper: Map event type to UFunction name
//-----------------------------------------------------------------------------

static bool GetEventFunctionInfo(const FString& InEventType, FName& OutFunctionName)
{
	static TMap<FString, FName> eventMap;
	if (eventMap.Num() == 0)
	{
		eventMap.Add(TEXT("BeginPlay"), FName("ReceiveBeginPlay"));
		eventMap.Add(TEXT("Tick"), FName("ReceiveTick"));
		eventMap.Add(TEXT("EndPlay"), FName("ReceiveEndPlay"));
		eventMap.Add(TEXT("ActorBeginOverlap"), FName("ReceiveActorBeginOverlap"));
		eventMap.Add(TEXT("ActorEndOverlap"), FName("ReceiveActorEndOverlap"));
		eventMap.Add(TEXT("AnyDamage"), FName("ReceiveAnyDamage"));
		eventMap.Add(TEXT("Hit"), FName("ReceiveHit"));
	}

	const FName* found = eventMap.Find(InEventType);
	if (found)
	{
		OutFunctionName = *found;
		return true;
	}
	return false;
}

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_BlueprintGraph
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_BlueprintGraph);

FWN_MCP_CommandGroup_BlueprintGraph::FWN_MCP_CommandGroup_BlueprintGraph()
{

}

FWN_MCP_CommandGroup_BlueprintGraph::~FWN_MCP_CommandGroup_BlueprintGraph()
{
}

FString FWN_MCP_CommandGroup_BlueprintGraph::GetName() const
{
	return FString("BlueprintGraph");
}

FString FWN_MCP_CommandGroup_BlueprintGraph::GetApplicationName() const
{
	return FString("WN_MCP_WORLD");
}

void FWN_MCP_CommandGroup_BlueprintGraph::OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "read_blueprint_graph", "Read Blueprint graph nodes and connections");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_event_node", "Add an event node to Blueprint graph");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_function_call_node", "Add a function call node to Blueprint graph");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_variable_get_node", "Add a variable getter node to Blueprint graph");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_variable_set_node", "Add a variable setter node to Blueprint graph");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "connect_nodes", "Connect two nodes in Blueprint graph");
	WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "disconnect_nodes", "Disconnect two nodes in Blueprint graph");
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_BlueprintGraph::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// read_blueprint_graph
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("read_blueprint_graph")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		TArray<TSharedPtr<FJsonValue>> nodeArray;
		for (UEdGraphNode* node : eventGraph->Nodes)
		{
			if (!node)
			{
				continue;
			}

			TSharedPtr<FJsonObject> nodeObj = MakeShareable(new FJsonObject());
			nodeObj->SetStringField(TEXT("node_id"), node->NodeGuid.ToString());
			nodeObj->SetStringField(TEXT("node_class"), node->GetClass()->GetName());
			nodeObj->SetStringField(TEXT("node_title"), node->GetNodeTitle(ENodeTitleType::FullTitle).ToString());

			TArray<TSharedPtr<FJsonValue>> posArray;
			posArray.Add(MakeShareable(new FJsonValueNumber(node->NodePosX)));
			posArray.Add(MakeShareable(new FJsonValueNumber(node->NodePosY)));
			nodeObj->SetArrayField(TEXT("position"), posArray);

			// Pins with connection info
			TArray<TSharedPtr<FJsonValue>> pinsArray;
			for (const UEdGraphPin* pin : node->Pins)
			{
				if (!pin || pin->bHidden)
				{
					continue;
				}

				TSharedPtr<FJsonObject> pinObj = BuildPinInfo(pin);

				// Add connection info
				TArray<TSharedPtr<FJsonValue>> connArray;
				for (const UEdGraphPin* linkedPin : pin->LinkedTo)
				{
					if (linkedPin && linkedPin->GetOwningNode())
					{
						TSharedPtr<FJsonObject> connObj = MakeShareable(new FJsonObject());
						connObj->SetStringField(TEXT("node_id"), linkedPin->GetOwningNode()->NodeGuid.ToString());
						connObj->SetStringField(TEXT("pin_name"), linkedPin->PinName.ToString());
						connArray.Add(MakeShareable(new FJsonValueObject(connObj)));
					}
				}
				pinObj->SetArrayField(TEXT("connected_to"), connArray);

				pinsArray.Add(MakeShareable(new FJsonValueObject(pinObj)));
			}
			nodeObj->SetArrayField(TEXT("pins"), pinsArray);

			nodeArray.Add(MakeShareable(new FJsonValueObject(nodeObj)));
		}

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("blueprint_name"), blueprint->GetName());
		InResultPtr->SetStringField(TEXT("graph_name"), TEXT("EventGraph"));
		InResultPtr->SetNumberField(TEXT("node_count"), nodeArray.Num());
		InResultPtr->SetArrayField(TEXT("nodes"), nodeArray);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_event_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_event_node")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString eventType;
		if (!InParamsPtr->TryGetStringField(TEXT("event_type"), eventType))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: event_type"));
		}

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Map event type to function name
		FName functionName;
		if (!GetEventFunctionInfo(eventType, functionName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Unsupported event type: %s. Supported: BeginPlay, Tick, EndPlay, ActorBeginOverlap, ActorEndOverlap, AnyDamage, Hit"), *eventType));
		}

		// Optional position
		int32 posX = 0, posY = 0;
		const TArray<TSharedPtr<FJsonValue>>* posArray;
		if (InParamsPtr->TryGetArrayField(TEXT("node_position"), posArray) && posArray->Num() >= 2)
		{
			posX = static_cast<int32>((*posArray)[0]->AsNumber());
			posY = static_cast<int32>((*posArray)[1]->AsNumber());
		}

		// Create event node
		UClass* ownerClass = blueprint->ParentClass ? blueprint->ParentClass.Get() : AActor::StaticClass();
		UK2Node_Event* eventNode = NewObject<UK2Node_Event>(eventGraph);
		eventNode->CreateNewGuid();
		eventNode->EventReference.SetExternalMember(functionName, ownerClass);
		eventNode->bOverrideFunction = true;
		eventNode->NodePosX = posX;
		eventNode->NodePosY = posY;
		eventNode->AllocateDefaultPins();
		eventGraph->AddNode(eventNode, false, false);

		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("node_id"), eventNode->NodeGuid.ToString());
		InResultPtr->SetStringField(TEXT("event_type"), eventType);
		InResultPtr->SetArrayField(TEXT("pins"), BuildPinsArray(eventNode));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_function_call_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_function_call_node")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString functionName;
		if (!InParamsPtr->TryGetStringField(TEXT("function_name"), functionName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: function_name"));
		}

		FString targetClass;
		InParamsPtr->TryGetStringField(TEXT("target_class"), targetClass);

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Find the UFunction
		UFunction* function = FindFunctionByName(functionName, targetClass, blueprint);
		if (!function)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Function not found: %s"), *functionName));
		}

		// Optional position
		int32 posX = 0, posY = 0;
		const TArray<TSharedPtr<FJsonValue>>* posArray;
		if (InParamsPtr->TryGetArrayField(TEXT("node_position"), posArray) && posArray->Num() >= 2)
		{
			posX = static_cast<int32>((*posArray)[0]->AsNumber());
			posY = static_cast<int32>((*posArray)[1]->AsNumber());
		}

		// Create function call node
		UK2Node_CallFunction* callNode = NewObject<UK2Node_CallFunction>(eventGraph);
		callNode->CreateNewGuid();
		callNode->FunctionReference.SetExternalMember(function->GetFName(), function->GetOwnerClass());
		callNode->NodePosX = posX;
		callNode->NodePosY = posY;
		callNode->AllocateDefaultPins();
		eventGraph->AddNode(callNode, false, false);

		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("node_id"), callNode->NodeGuid.ToString());
		InResultPtr->SetStringField(TEXT("function_name"), functionName);
		InResultPtr->SetArrayField(TEXT("pins"), BuildPinsArray(callNode));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_variable_get_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_variable_get_node")))
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

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Validate variable exists in blueprint
		FName varFName(*variableName);
		bool bVarExists = blueprint->NewVariables.ContainsByPredicate([&varFName](const FBPVariableDescription& V){ return V.VarName == varFName; });
		if (!bVarExists)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Variable '%s' does not exist in blueprint"), *variableName));
		}

		// Optional position
		int32 posX = 0, posY = 0;
		const TArray<TSharedPtr<FJsonValue>>* posArray;
		if (InParamsPtr->TryGetArrayField(TEXT("node_position"), posArray) && posArray->Num() >= 2)
		{
			posX = static_cast<int32>((*posArray)[0]->AsNumber());
			posY = static_cast<int32>((*posArray)[1]->AsNumber());
		}

		// Create variable get node
		UK2Node_VariableGet* getNode = NewObject<UK2Node_VariableGet>(eventGraph);
		getNode->CreateNewGuid();
		getNode->VariableReference.SetSelfMember(FName(*variableName));
		getNode->NodePosX = posX;
		getNode->NodePosY = posY;
		getNode->AllocateDefaultPins();
		eventGraph->AddNode(getNode, false, false);

		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("node_id"), getNode->NodeGuid.ToString());
		InResultPtr->SetStringField(TEXT("variable_name"), variableName);
		InResultPtr->SetArrayField(TEXT("pins"), BuildPinsArray(getNode));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_variable_set_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_variable_set_node")))
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

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Validate variable exists in blueprint
		FName varFName(*variableName);
		bool bVarExists = blueprint->NewVariables.ContainsByPredicate([&varFName](const FBPVariableDescription& V){ return V.VarName == varFName; });
		if (!bVarExists)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Variable '%s' does not exist in blueprint"), *variableName));
		}

		// Optional position
		int32 posX = 0, posY = 0;
		const TArray<TSharedPtr<FJsonValue>>* posArray;
		if (InParamsPtr->TryGetArrayField(TEXT("node_position"), posArray) && posArray->Num() >= 2)
		{
			posX = static_cast<int32>((*posArray)[0]->AsNumber());
			posY = static_cast<int32>((*posArray)[1]->AsNumber());
		}

		// Create variable set node
		UK2Node_VariableSet* setNode = NewObject<UK2Node_VariableSet>(eventGraph);
		setNode->CreateNewGuid();
		setNode->VariableReference.SetSelfMember(FName(*variableName));
		setNode->NodePosX = posX;
		setNode->NodePosY = posY;
		setNode->AllocateDefaultPins();
		eventGraph->AddNode(setNode, false, false);

		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetStringField(TEXT("node_id"), setNode->NodeGuid.ToString());
		InResultPtr->SetStringField(TEXT("variable_name"), variableName);
		InResultPtr->SetArrayField(TEXT("pins"), BuildPinsArray(setNode));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// connect_nodes
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("connect_nodes")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString sourceNodeId;
		if (!InParamsPtr->TryGetStringField(TEXT("source_node_id"), sourceNodeId))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: source_node_id"));
		}

		FString sourcePinName;
		if (!InParamsPtr->TryGetStringField(TEXT("source_pin_name"), sourcePinName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: source_pin_name"));
		}

		FString targetNodeId;
		if (!InParamsPtr->TryGetStringField(TEXT("target_node_id"), targetNodeId))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: target_node_id"));
		}

		FString targetPinName;
		if (!InParamsPtr->TryGetStringField(TEXT("target_pin_name"), targetPinName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: target_pin_name"));
		}

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Find source node and pin
		UEdGraphNode* sourceNode = FindNodeByGuid(eventGraph, sourceNodeId);
		if (!sourceNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Source node not found: %s"), *sourceNodeId));
		}

		UEdGraphPin* sourcePin = sourceNode->FindPin(FName(*sourcePinName));
		if (!sourcePin)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Source pin not found: %s"), *sourcePinName));
		}

		// Find target node and pin
		UEdGraphNode* targetNode = FindNodeByGuid(eventGraph, targetNodeId);
		if (!targetNode)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Target node not found: %s"), *targetNodeId));
		}

		UEdGraphPin* targetPin = targetNode->FindPin(FName(*targetPinName));
		if (!targetPin)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Target pin not found: %s"), *targetPinName));
		}

		// Try to create connection
		const UEdGraphSchema_K2* schema = GetDefault<UEdGraphSchema_K2>();
		bool bConnected = schema->TryCreateConnection(sourcePin, targetPin);

		if (!bConnected)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to connect %s.%s -> %s.%s"), *sourceNodeId, *sourcePinName, *targetNodeId, *targetPinName));
		}

		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// disconnect_nodes
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("disconnect_nodes")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString nodeId;
		if (!InParamsPtr->TryGetStringField(TEXT("node_id"), nodeId))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: node_id"));
		}

		FString pinName;
		if (!InParamsPtr->TryGetStringField(TEXT("pin_name"), pinName))
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: pin_name"));
		}

		UBlueprint* blueprint = FWN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		UEdGraphNode* node = FindNodeByGuid(eventGraph, nodeId);
		if (!node)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Node not found: %s"), *nodeId));
		}

		UEdGraphPin* pin = node->FindPin(FName(*pinName));
		if (!pin)
		{
			WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Pin not found: %s"), *pinName));
		}

		int32 disconnectedCount = pin->LinkedTo.Num();
		const UEdGraphSchema_K2* schema = GetDefault<UEdGraphSchema_K2>();
		schema->BreakPinLinks(*pin, true);

		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetNumberField(TEXT("disconnected_count"), disconnectedCount);
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
