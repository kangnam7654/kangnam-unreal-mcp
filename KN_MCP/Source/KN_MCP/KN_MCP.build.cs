// Copyright Kangnam Kim. All Rights Reserved.

using UnrealBuildTool;

public class KN_MCP : ModuleRules
{
	public KN_MCP(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		bEnableExceptions = true;

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
				"Networking",
				"Sockets",
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
				"Projects",
				"AssetRegistry"
			}
		);

		// Kismet/Blueprint 관련 모듈은 에디터 빌드에서만 추가. 런타임 패키징 시 EditorStyle 등 에디터 전용 인스턴스 참조 방지.
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