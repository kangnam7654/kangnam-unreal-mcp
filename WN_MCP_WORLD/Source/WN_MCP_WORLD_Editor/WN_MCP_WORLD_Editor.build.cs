// Copyright Kangnam Kim. All Rights Reserved.

using UnrealBuildTool;

public class WN_MCP_WORLD_Editor : ModuleRules
{
	public WN_MCP_WORLD_Editor(ReadOnlyTargetRules Target) : base(Target)
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
				"Json",
				"JsonUtilities"
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"UnrealEd",
				"Kismet",
				"KismetCompiler",
				"BlueprintGraph",
				"AssetRegistry",
				"EditorScriptingUtilities",
				"WN_MCP",
				"WN_MCP_WORLD"
			}
		);

		DynamicallyLoadedModuleNames.AddRange(
			new string[]
			{
				// add any modules that your module loads dynamically here
			}
		);
	}
}
