// Copyright WemadeNext, Inc. All Rights Reserved.

using UnrealBuildTool;

public class WN_MCPTest : ModuleRules
{
	public WN_MCPTest(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicIncludePaths.AddRange(
			new string[] {
				// add public include paths required here
			}
		);
		
		PrivateIncludePaths.AddRange(
			new string[] {
				// add other private include paths required here
			}
		);
		
		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"InputCore",
				"Networking",
				"Sockets",
				"HTTP",
				"Json",
				"JsonUtilities",
				"DeveloperSettings"
			}
		);
		
		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"Slate",
				"SlateCore",
				"UMG",
				"Projects",
				"AssetRegistry",
				"WN_MCP"
			}
		);

		// Kismet/Blueprint 관련 모듈은 에디터 전용. 게임 타겟 패키징 시 EditorStyle 비에디터 인스턴스 에러 방지.
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(
				new string[]
				{
					"Kismet",
					"KismetCompiler",
					"BlueprintGraph"
				}
			);
		}

		DynamicallyLoadedModuleNames.AddRange(
			new string[]
			{
				// add any modules that your module loads dynamically here
			}
		);
	}
} 