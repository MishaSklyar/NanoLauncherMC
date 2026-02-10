import dearpygui.dearpygui as dpg
import threading
import queue
from core.launcher import NanoCore
from core.mods import ModManager
import time

# --- Architecture ---
# Logic runs in threads -> Pushes GUI updates to Queue -> Main Thread renders Queue
# This prevents SEGFAULTS on macOS.

command_queue = queue.Queue()
core = NanoCore()
manager = ModManager(core.game_directory)

def queue_ui_task(func, *args, **kwargs):
    """Push a UI function to run on the main thread."""
    command_queue.put((func, args, kwargs))

def ui_loop():
    """Process pending UI updates."""
    while not command_queue.empty():
        try:
            func, args, kwargs = command_queue.get_nowait()
            func(*args, **kwargs)
        except queue.Empty:
            break

# --- UI Callbacks (Executed in Threads usually) ---

def log(message, type="INFO"):
    def _update():
        # Add new text item to the child window
        # Color coding based on type
        color = (200, 200, 200)
        if type == "ERROR": color = (255, 50, 50)
        elif type == "SUCCESS": color = (50, 255, 50)
        elif type == "SYSTEM": color = (50, 150, 255)
        
        dpg.add_text(f"[{type}] {message}", parent="console_output", color=color)
        
        # Scroll to bottom
        y_max = dpg.get_y_scroll_max("console_output")
        dpg.set_y_scroll("console_output", y_max)
    
    queue_ui_task(_update)

def refresh_versions_ui():
    versions = core.get_installed_versions()
    ids = [v['id'] for v in versions]
    def _update():
        dpg.configure_item("version_combo", items=ids)
        if ids:
             dpg.set_value("version_combo", ids[0])
        else:
             dpg.configure_item("version_combo", items=["No versions found"])
    queue_ui_task(_update)

def launch_game(sender, app_data):
    ver = dpg.get_value("version_combo")
    user = dpg.get_value("username_input")
    ram = dpg.get_value("ram_slider")
    
    if not user:
        log("Username is required!", "ERROR")
        return

    dpg.configure_item("launch_btn", label="Running...", enabled=False)
    log(f"Launching {ver}...", "SYSTEM")

    def task():
        try:
            core.launch(ver, user, ram)
            log("Process launched.", "SUCCESS")
        except Exception as e:
            log(str(e), "ERROR")
        finally:
            queue_ui_task(lambda: dpg.configure_item("launch_btn", label="LAUNCH GAME", enabled=True))

    threading.Thread(target=task, daemon=True).start()

def install_version_btn(sender, app_data):
    ver = dpg.get_value("install_ver_input")
    loader = dpg.get_value("loader_combo")
    
    if not ver:
        log("Enter a version.", "ERROR")
        return
        
    dpg.configure_item("install_btn", label="Installing...", enabled=False)
    log(f"Starting optimized install of {ver}...", "SYSTEM")
    
    # Callback for detailed logging
    def status_callback(status):
        log(status, "INSTALL")
        
    def progress_callback(curr, max_val):
        # Optional: could update a progress bar here
        pass

    callbacks = {
        "setStatus": status_callback,
        "setProgress": progress_callback,
        "setMax": lambda m: None
    }

    def task():
        try:
            vid = core.install_version(ver, loader if loader != "vanilla" else None, callback=callbacks)
            log(f"Successfully installed {vid}!", "SUCCESS")
            # Trigger refresh of play tab
            refresh_versions_ui()
        except Exception as e:
             log(f"Install failed: {str(e)}", "ERROR")
        finally:
             queue_ui_task(lambda: dpg.configure_item("install_btn", label="INSTALL", enabled=True))

    threading.Thread(target=task, daemon=True).start()

def search_mods_btn(sender, app_data):
    query = dpg.get_value("mod_search_input")
    if not query: return
    
    # Clear table
    dpg.delete_item("mod_results_table", children_only=True)
    dpg.add_text("Searching...", parent="mod_results_table", tag="searching_txt")
    
    def task():
        results = manager.search_modrinth(query)
        
        def _build_table():
            dpg.delete_item("searching_txt")
            # Clear previous results but we must restore columns!
            # Actually, let's just clear rows. 
            # DPG Trick: Create a 'staging' row or manage IDs? 
            # Simpler: Just re-create columns.
            dpg.delete_item("mod_results_table", children_only=True)
            dpg.add_table_column(label="Mod Name", parent="mod_results_table", width_stretch=True)
            dpg.add_table_column(label="Author", parent="mod_results_table", width_fixed=True, init_width_or_weight=100)
            dpg.add_table_column(label="Action", parent="mod_results_table", width_fixed=True, init_width_or_weight=80)

            if not results:
                with dpg.table_row(parent="mod_results_table"):
                    dpg.add_text("No results found.")
                return

            for mod in results:
                # Unique tags are needed if we want to reference them, but rows don't need distinct tags usually
                with dpg.table_row(parent="mod_results_table"):
                    dpg.add_text(mod['title'])
                    dpg.add_text(mod['author'])
                    
                    # Store mod data in user_data for valid access
                    dpg.add_button(label="Install", user_data=mod, callback=install_mod_callback)
        
        queue_ui_task(_build_table)

    threading.Thread(target=task, daemon=True).start()

def install_mod_callback(sender, app_data, user_data):
    # user_data contains the mod dict
    mod = user_data
    t_ver = dpg.get_value("mod_target_ver")
    loader = dpg.get_value("mod_loader_combo")
    
    log(f"Installing {mod['title']}...", "MODS")
    
    # Disable button
    dpg.configure_item(sender, label="...", enabled=False)

    def task():
        success = manager.install_mod(mod['project_id'], t_ver, loader)
        def _finish():
            if success:
                dpg.configure_item(sender, label="Done")
                log(f"Installed {mod['title']}", "SUCCESS")
            else:
                dpg.configure_item(sender, label="Failed", enabled=True)
                log(f"Failed to install {mod['title']}", "ERROR")
        queue_ui_task(_finish)
        
    threading.Thread(target=task, daemon=True).start()

# --- Main Construction ---

def create_gui():
    dpg.create_context()
    dpg.create_viewport(title='Nano Launcher', width=950, height=650)
    
    # Theme: "Hacker"
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (10, 10, 12))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 40, 40))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 60, 60))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (30, 200, 100))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 20, 20)

    dpg.bind_theme(global_theme)

    with dpg.window(tag="Primary Window", no_title_bar=True):
        
        dpg.add_text("NANO LAUNCHER", color=(30, 200, 100))
        dpg.add_separator()
        
        with dpg.tab_bar():
            
            with dpg.tab(label=" PLAY "):
                dpg.add_spacer(height=20)
                with dpg.group(horizontal=True):
                    dpg.add_text("Version:", color=(150, 150, 150))
                    dpg.add_combo(tag="version_combo", width=300)
                
                with dpg.group(horizontal=True):
                    dpg.add_text("User:   ", color=(150, 150, 150))
                    dpg.add_input_text(tag="username_input", default_value="Steve", width=300)
                
                with dpg.group(horizontal=True):
                    dpg.add_text("RAM:    ", color=(150, 150, 150))
                    dpg.add_slider_int(tag="ram_slider", min_value=1024, max_value=16384, default_value=4096, width=300)
                
                dpg.add_spacer(height=20)
                dpg.add_button(tag="launch_btn", label="LAUNCH GAME", callback=launch_game, width=400, height=60)
            
            with dpg.tab(label=" INSTALL "):
                dpg.add_spacer(height=20)
                dpg.add_text("Install new instance:")
                dpg.add_input_text(tag="install_ver_input", hint="e.g. 1.20.1", width=300)
                dpg.add_combo(tag="loader_combo", items=["vanilla", "fabric", "forge", "quilt"], default_value="vanilla", width=300)
                dpg.add_spacer(height=10)
                dpg.add_button(tag="install_btn", label="INSTALL", callback=install_version_btn, width=200)

            with dpg.tab(label=" MODS "):
                dpg.add_spacer(height=20)
                with dpg.group(horizontal=True):
                    dpg.add_input_text(tag="mod_search_input", hint="Search Modrinth...", width=400)
                    dpg.add_button(label="Search", callback=search_mods_btn)
                
                dpg.add_spacer(height=10)
                dpg.add_text("Target:", color=(150, 150, 150))
                with dpg.group(horizontal=True):
                     dpg.add_input_text(tag="mod_target_ver", default_value="1.20.1", width=100)
                     dpg.add_combo(tag="mod_loader_combo", items=["fabric", "forge", "quilt"], default_value="fabric", width=100)

                dpg.add_spacer(height=10)
                # Results Table
                with dpg.table(tag="mod_results_table", header_row=True, height=300, scrollY=True, 
                               borders_innerH=True, borders_outerH=True, row_background=True):
                    dpg.add_table_column(label="Name", width_stretch=True)
                    dpg.add_table_column(label="Author", width_fixed=True, init_width_or_weight=100)
                    dpg.add_table_column(label="Action", width_fixed=True, init_width_or_weight=80)
            
            with dpg.tab(label=" ABOUT "):
                dpg.add_text("Nano Launcher v1.0")
                dpg.add_text("Written in Python. Powered by Dear PyGui.")
                dpg.add_text("Lightweight. Fast. Open Source.")

        # Console Log Area
        dpg.add_spacer(height=20)
        dpg.add_separator()
        dpg.add_text("SYSTEM LOG", color=(100, 100, 100))
        # Use child window for log
        with dpg.child_window(tag="console_output", height=150, width=-1, border=True):
             pass

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    
    # Load initial data
    refresh_versions_ui()

    # --- MANUAL RENDER LOOP ---
    # This keeps the main thread free to handle OS events and our UI queue
    while dpg.is_dearpygui_running():
        # process queue
        ui_loop()
        # render frame
        dpg.render_dearpygui_frame()

    dpg.destroy_context()

if __name__ == "__main__":
    create_gui()
