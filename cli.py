import argparse
import sys
from core.launcher import NanoCore

def main():
    parser = argparse.ArgumentParser(description="Nano Launcher - The Simplest & Most Powerful Minecraft Launcher")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install Command
    install_parser = subparsers.add_parser("install", help="Install a Minecraft version")
    install_parser.add_argument("version", help="Minecraft version (e.g., 1.20.1)")
    install_parser.add_argument("--loader", choices=["fabric", "forge", "quilt", "vanilla"], default="vanilla", help="Mod loader to install")

    # Launch Command
    launch_parser = subparsers.add_parser("launch", help="Launch Minecraft")
    launch_parser.add_argument("version", help="Version ID to launch (e.g., 1.20.1 or fabric-loader-1.20.1)")
    launch_parser.add_argument("username", help="Offline username")
    launch_parser.add_argument("--ram", type=int, default=2048, help="RAM in MB (Default: 2048)")

    # List Command
    list_parser = subparsers.add_parser("list", help="List installed versions")

    args = parser.parse_args()
    
    core = NanoCore()

    if args.command == "install":
        print(f"Starting installation for {args.version} ({args.loader})...")
        try:
            installed_id = core.install_version(args.version, args.loader if args.loader != "vanilla" else None)
            print(f"Successfully installed: {installed_id}")
        except Exception as e:
            print(f"Error installing: {e}")

    elif args.command == "launch":
        print(f"Launching {args.version} as {args.username}...")
        try:
            core.launch(args.version, args.username, args.ram)
        except Exception as e:
            print(f"Error launching: {e}")

    elif args.command == "list":
        versions = core.get_installed_versions()
        for v in versions:
            print(f"- {v['id']} ({v['type']})")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
