import requests
import os

class ModManager:
    def __init__(self, game_directory):
        self.game_directory = game_directory
        self.mods_path = os.path.join(game_directory, "mods")
        if not os.path.exists(self.mods_path):
            os.makedirs(self.mods_path)

    def search_modrinth(self, query, version=None, loader=None):
        """Searches Modrinth for mods."""
        url = "https://api.modrinth.com/v2/search"
        params = {
            "query": query,
            "limit": 5
        }
        
        facets = []
        if version:
            facets.append(f'["versions:{version}"]')
        if loader:
            facets.append(f'["categories:{loader}"]')
            
        if facets:
            params["facets"] = "[" + ",".join(facets) + "]"

        headers = {
            "User-Agent": "NanoLauncher/1.0 (launcher@nano.app)"
        }
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json().get("hits", [])
        return []

    def install_mod(self, project_id, version, loader):
        """Downloads the correct version file for the mod. Client-side filtering for reliability."""
        url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        
        headers = {
             "User-Agent": "NanoLauncher/1.0 (launcher@nano.app)"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch versions: {response.text}")
                return False
                
            versions = response.json()
            
            target_version = None
            
            for v in versions:
                # Check if compatible with game version
                if version not in v["game_versions"]:
                    continue
                # Check if compatible with loader
                if loader not in v["loaders"]:
                    continue
                
                target_version = v
                break
            
            if not target_version:
                print(f"No compatible version found for {project_id} on {version} ({loader})")
                return False
            
            # Download primary file
            primary_file = target_version["files"][0]
            for f in target_version["files"]:
                if f["primary"]:
                    primary_file = f
                    break
            
            file_url = primary_file["url"]
            filename = primary_file["filename"]
            
            print(f"Downloading {filename}...")
            r = requests.get(file_url)
            
            # Ensure mods dir exists for this instance specifically logic to be added, currently shared
            # In a real launcher, we'd have instance separation. For Nano, let's keep it simple:
            # But wait, mods go into <game_dir>/mods usually.
            
            save_path = os.path.join(self.mods_path, filename)
            with open(save_path, "wb") as f:
                f.write(r.content)
                
            print(f"Installed {filename} to {self.mods_path}")
            return True
            
        except Exception as e:
            print(f"Error installing mod: {e}")
            return False
