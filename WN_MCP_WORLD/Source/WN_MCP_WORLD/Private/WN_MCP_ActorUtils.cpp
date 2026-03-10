#include "WN_MCP_ActorUtils.h"

#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

//-----------------------------------------------------------------------------
// FWN_MCP_ActorUtils
//-----------------------------------------------------------------------------

AActor* FWN_MCP_ActorUtils::FindActorByName(const FString& InActorName)
{
	TArray<AActor*> allActors;
	UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), allActors);

	for (AActor* actor : allActors)
	{
		if (actor && actor->GetName() == InActorName)
		{
			return actor;
		}
	}

	return nullptr;
}
