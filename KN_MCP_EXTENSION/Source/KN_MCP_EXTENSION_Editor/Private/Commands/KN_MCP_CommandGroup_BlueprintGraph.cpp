#include "KN_MCP_CommandGroup_BlueprintGraph.h"
#include "KN_MCP_BlueprintUtils.h"
#include "KN_MCP_Module.h"

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
	// Fallback: return the first UbergraphPage if no graph named "EventGraph" exists
	if (InBlueprint->UbergraphPages.Num() > 0)
	{
		return InBlueprint->UbergraphPages[0];
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
	// Const map built once; no thread-safety concern since it's immutable after initialization.
	static const TMap<FString, FName> EventMap = []()
	{
		TMap<FString, FName> map;
		map.Add(TEXT("BeginPlay"), FName("ReceiveBeginPlay"));
		map.Add(TEXT("Tick"), FName("ReceiveTick"));
		map.Add(TEXT("EndPlay"), FName("ReceiveEndPlay"));
		map.Add(TEXT("ActorBeginOverlap"), FName("ReceiveActorBeginOverlap"));
		map.Add(TEXT("ActorEndOverlap"), FName("ReceiveActorEndOverlap"));
		map.Add(TEXT("AnyDamage"), FName("ReceiveAnyDamage"));
		map.Add(TEXT("Hit"), FName("ReceiveHit"));
		return map;
	}();

	const FName* found = EventMap.Find(InEventType);
	if (found)
	{
		OutFunctionName = *found;
		return true;
	}
	return false;
}

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_BlueprintGraph
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_BlueprintGraph);

FKN_MCP_CommandGroup_BlueprintGraph::FKN_MCP_CommandGroup_BlueprintGraph()
{

}

FKN_MCP_CommandGroup_BlueprintGraph::~FKN_MCP_CommandGroup_BlueprintGraph()
{
}

FString FKN_MCP_CommandGroup_BlueprintGraph::GetName() const
{
	return FString("BlueprintGraph");
}

FString FKN_MCP_CommandGroup_BlueprintGraph::GetApplicationName() const
{
	return FString("KN_MCP_EXTENSION");
}

void FKN_MCP_CommandGroup_BlueprintGraph::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "read_blueprint_graph");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_event_node");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_function_call_node");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_variable_get_node");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "add_variable_set_node");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "connect_nodes");
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "disconnect_nodes");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_BlueprintGraph::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// read_blueprint_graph
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("read_blueprint_graph")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_event_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_event_node")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString eventType;
		if (!InParamsPtr->TryGetStringField(TEXT("event_type"), eventType))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: event_type"));
		}

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Map event type to function name
		FName functionName;
		if (!GetEventFunctionInfo(eventType, functionName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
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

		// Check for duplicate event node
		for (UEdGraphNode* existingNode : eventGraph->Nodes)
		{
			UK2Node_Event* existingEvent = Cast<UK2Node_Event>(existingNode);
			if (existingEvent && existingEvent->EventReference.GetMemberName() == functionName)
			{
				KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
					*FString::Printf(TEXT("Event '%s' already exists in Blueprint"), *eventType));
			}
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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_function_call_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_function_call_node")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString functionName;
		if (!InParamsPtr->TryGetStringField(TEXT("function_name"), functionName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: function_name"));
		}

		FString targetClass;
		InParamsPtr->TryGetStringField(TEXT("target_class"), targetClass);

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Find the UFunction
		UFunction* function = FindFunctionByName(functionName, targetClass, blueprint);
		if (!function)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
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
		UClass* ownerClass = function->GetOwnerClass();
		if (!ownerClass)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Cannot determine owner class for function '%s'"), *functionName));
		}

		UK2Node_CallFunction* callNode = NewObject<UK2Node_CallFunction>(eventGraph);
		callNode->CreateNewGuid();
		callNode->FunctionReference.SetExternalMember(function->GetFName(), ownerClass);
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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_variable_get_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_variable_get_node")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString variableName;
		if (!InParamsPtr->TryGetStringField(TEXT("variable_name"), variableName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_name"));
		}

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Validate variable exists in blueprint
		FName varFName(*variableName);
		bool bVarExists = blueprint->NewVariables.ContainsByPredicate([&varFName](const FBPVariableDescription& V){ return V.VarName == varFName; });
		if (!bVarExists)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// add_variable_set_node
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("add_variable_set_node")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString variableName;
		if (!InParamsPtr->TryGetStringField(TEXT("variable_name"), variableName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: variable_name"));
		}

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Validate variable exists in blueprint
		FName varFName(*variableName);
		bool bVarExists = blueprint->NewVariables.ContainsByPredicate([&varFName](const FBPVariableDescription& V){ return V.VarName == varFName; });
		if (!bVarExists)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
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
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// connect_nodes
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("connect_nodes")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString sourceNodeId;
		if (!InParamsPtr->TryGetStringField(TEXT("source_node_id"), sourceNodeId))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: source_node_id"));
		}

		FString sourcePinName;
		if (!InParamsPtr->TryGetStringField(TEXT("source_pin_name"), sourcePinName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: source_pin_name"));
		}

		FString targetNodeId;
		if (!InParamsPtr->TryGetStringField(TEXT("target_node_id"), targetNodeId))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: target_node_id"));
		}

		FString targetPinName;
		if (!InParamsPtr->TryGetStringField(TEXT("target_pin_name"), targetPinName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: target_pin_name"));
		}

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		// Find source node and pin
		UEdGraphNode* sourceNode = FindNodeByGuid(eventGraph, sourceNodeId);
		if (!sourceNode)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Source node not found: %s"), *sourceNodeId));
		}

		UEdGraphPin* sourcePin = sourceNode->FindPin(FName(*sourcePinName));
		if (!sourcePin)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Source pin not found: %s"), *sourcePinName));
		}

		// Find target node and pin
		UEdGraphNode* targetNode = FindNodeByGuid(eventGraph, targetNodeId);
		if (!targetNode)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Target node not found: %s"), *targetNodeId));
		}

		UEdGraphPin* targetPin = targetNode->FindPin(FName(*targetPinName));
		if (!targetPin)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Target pin not found: %s"), *targetPinName));
		}

		// Try to create connection
		const UEdGraphSchema_K2* schema = GetDefault<UEdGraphSchema_K2>();
		bool bConnected = schema->TryCreateConnection(sourcePin, targetPin);

		if (!bConnected)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Failed to connect %s.%s -> %s.%s"), *sourceNodeId, *sourcePinName, *targetNodeId, *targetPinName));
		}

		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	//-------------------------------------------------------------------------
	// disconnect_nodes
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("disconnect_nodes")))
	{
		FString blueprintName;
		if (!InParamsPtr.IsValid() || !InParamsPtr->TryGetStringField(TEXT("blueprint_name"), blueprintName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: blueprint_name"));
		}

		FString nodeId;
		if (!InParamsPtr->TryGetStringField(TEXT("node_id"), nodeId))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: node_id"));
		}

		FString pinName;
		if (!InParamsPtr->TryGetStringField(TEXT("pin_name"), pinName))
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS, TEXT("Missing required parameter: pin_name"));
		}

		UBlueprint* blueprint = FKN_MCP_BlueprintUtils::FindBlueprintByName(blueprintName);
		if (!blueprint)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED,
				*FString::Printf(TEXT("Blueprint not found: %s"), *blueprintName));
		}

		UEdGraph* eventGraph = FindEventGraph(blueprint);
		if (!eventGraph)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_COMMAND_FAILED, TEXT("EventGraph not found"));
		}

		UEdGraphNode* node = FindNodeByGuid(eventGraph, nodeId);
		if (!node)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Node not found: %s"), *nodeId));
		}

		UEdGraphPin* pin = node->FindPin(FName(*pinName));
		if (!pin)
		{
			KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_INVALID_PARAMS,
				*FString::Printf(TEXT("Pin not found: %s"), *pinName));
		}

		int32 disconnectedCount = pin->LinkedTo.Num();
		const UEdGraphSchema_K2* schema = GetDefault<UEdGraphSchema_K2>();
		schema->BreakPinLinks(*pin, true);

		FBlueprintEditorUtils::MarkBlueprintAsModified(blueprint);

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("status"), TEXT("success"));
		InResultPtr->SetNumberField(TEXT("disconnected_count"), disconnectedCount);
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
