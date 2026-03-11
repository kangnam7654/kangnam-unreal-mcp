// Copyright Kangnam Kim. All Rights Reserved.

using UnrealBuildTool;

public class WN_MCP_WORLD : ModuleRules
{
	public WN_MCP_WORLD(ReadOnlyTargetRules Target) : base(Target)
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
				"Projects",
				"WN_MCP"
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
