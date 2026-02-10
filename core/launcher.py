import minecraft_launcher_lib
import subprocess
import sys
import os
import uuid
import platform
import json

class NanoCore:
    def __init__(self, game_directory=None):
        if not game_directory:
            # Portable by default OR standard location
            if platform.system() == "Windows":
                 self.game_directory = os.path.join(os.environ["APPDATA"], ".nano_launcher")
            elif platform.system() == "Darwin":
                 self.game_directory = os.path.expanduser("~/Library/Application Support/nano_launcher")
            else:
                 self.game_directory = os.path.expanduser("~/.nano_launcher")
        else:
            self.game_directory = game_directory
        
        if not os.path.exists(self.game_directory):
            os.makedirs(self.game_directory)

    def get_installed_versions(self):
        return minecraft_launcher_lib.utils.get_installed_versions(self.game_directory)

    def install_version(self, version_id, loader=None, callback=None):
        """Installs a specific version. Supports installing Fabric/Forge/Quilt directly."""
        print(f"Installing {version_id}...")
        
        # Default empty callback to avoid errors
        if not callback:
            callback = {}
            
        # Ensure standard keys exist if a partial callback is provided
        if "setStatus" not in callback: callback["setStatus"] = print
        if "setProgress" not in callback: callback["setProgress"] = lambda *args: None
        if "setMax" not in callback: callback["setMax"] = lambda *args: None

        if loader == "fabric":
            print("Installing Fabric...")
            # fabric install doesn't support standard callback dict in older versions, checking...
            # modern minecraft-launcher-lib supports it usually.
            minecraft_launcher_lib.fabric.install_fabric(version_id, self.game_directory, callback=callback)
            version_id = minecraft_launcher_lib.fabric.get_fabric_version(version_id) # Update ID to modded one
        elif loader == "forge":
            print("Installing Forge...")
            minecraft_launcher_lib.forge.install_forge_version(version_id, self.game_directory, callback=callback)
            version_id = minecraft_launcher_lib.forge.find_forge_version(version_id)
        elif loader == "quilt":
            print("Installing Quilt...")
            minecraft_launcher_lib.quilt.install_quilt(version_id, self.game_directory, callback=callback)
            version_id = minecraft_launcher_lib.quilt.get_quilt_version(version_id)
        else:
            minecraft_launcher_lib.install.install_minecraft_version(version_id, self.game_directory, callback=callback)
            # Vanilla ID is just the version itself
            
        print(f"Installation of {version_id} complete.")
        return version_id

    def get_aikar_flags(self, ram_mb):
        """Returns optimization flags based on RAM allocation."""
        # Aikar's simplified flags for client performance
        flags = [
            f"-Xmx{ram_mb}M",
            f"-Xms{min(ram_mb, 2048)}M", # Don't alloc full RAM at start on potato PC
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+UseG1GC",
            "-XX:G1NewSizePercent=20",
            "-XX:G1ReservePercent=20",
            "-XX:MaxGCPauseMillis=50",
            "-XX:G1HeapRegionSize=32M",
            "-XX:+DisableExplicitGC",
            "-XX:+AlwaysPreTouch",
            "-XX:+ParallelRefProcEnabled"
        ]
        return flags

    def launch(self, version_id, username, ram_mb=2048, java_path=None):
        """Launches the localized version."""
        # Generate offline UUID
        options = {
            "username": username,
            "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, username)),
            "token": ""
        }

        # Find java if not provided
        if not java_path:
             # Try to find system java or runtime
             java_path = minecraft_launcher_lib.utils.get_java_executable()

        # Get command
        launch_command = minecraft_launcher_lib.command.get_minecraft_command(
            version=version_id,
            minecraft_directory=self.game_directory,
            options=options
        )

        # Inject optimizations
        # The library command is a list. We need to find where to inject JVM args.
        # Usually it's right after the java executable.
        optimization_flags = self.get_aikar_flags(ram_mb)
        
        # Insert flags at index 1 (after java executable)
        for flag in reversed(optimization_flags):
            launch_command.insert(1, flag)

        print(f"Launching with command: {' '.join(launch_command)}")
        
        # Execute
        subprocess.Popen(launch_command)
