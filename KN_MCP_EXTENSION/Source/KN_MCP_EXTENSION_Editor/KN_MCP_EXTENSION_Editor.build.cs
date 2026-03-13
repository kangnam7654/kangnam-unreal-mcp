// Copyright Kangnam Kim. All Rights Reserved.

using UnrealBuildTool;

public class KN_MCP_EXTENSION_Editor : ModuleRules
{
	public KN_MCP_EXTENSION_Editor(ReadOnlyTargetRules Target) : base(Target)
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
				"KN_MCP",
				"KN_MCP_EXTENSION"
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
