import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import importlib.util
from utils.logger import get_logger
from utils.result_handler import save_result

logger = get_logger()

def discover_modules(modules_dir="modules"):
    """Discovers available scan modules in the modules directory."""
    available_modules = {}
    
    if not os.path.exists(modules_dir):
        logger.warning(f"Modules directory '{modules_dir}' not found.")
        return available_modules

    for filename in os.listdir(modules_dir):
        # Explicit string conversion for Pyre
        fname = str(filename)
        if fname.endswith(".py") and not fname.startswith("__"):
            module_name = fname[:-3]  # type: ignore
            module_path = os.path.join(modules_dir, fname)

            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and hasattr(spec, "loader") and spec.loader:
                try:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    # Tell pyright that loader has exec_module
                    if hasattr(spec.loader, "exec_module"):
                        spec.loader.exec_module(module)  # type: ignore

                    # Verify the contract: 'run' function must exist
                    if hasattr(module, 'run') and callable(getattr(module, 'run')):
                        available_modules[module_name] = module
                        logger.debug(f"Successfully loaded module: {module_name}")
                    else:
                        logger.warning(f"Module '{module_name}' does not implement the run(config) contract. Skipping.")
                except Exception as e:
                    logger.error(f"Failed to load module '{module_name}': {e}")
            else:
                logger.error(f"Could not create spec for module '{module_name}'.")
        elif os.path.isdir(os.path.join(modules_dir, fname)) and not fname.startswith("__"):
            # Support package-style modules (subdirectory with __init__.py)
            init_path = os.path.join(modules_dir, fname, "__init__.py")
            if os.path.exists(init_path):
                spec = importlib.util.spec_from_file_location(
                    fname, init_path,
                    submodule_search_locations=[os.path.join(modules_dir, fname)]
                )
                if spec and spec.loader:
                    try:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[fname] = module
                        if hasattr(spec.loader, "exec_module"):
                            spec.loader.exec_module(module)  # type: ignore
                        if hasattr(module, 'run') and callable(getattr(module, 'run')):
                            available_modules[fname] = module
                            logger.debug(f"Successfully loaded package module: {fname}")
                        else:
                            logger.warning(f"Package '{fname}' does not implement the run(config) contract. Skipping.")
                    except Exception as e:
                        logger.error(f"Failed to load package module '{fname}': {e}")

    return available_modules

def start(config):
    """Displays the interactive menu and handles user selection."""
    print("\n--- CyberDeck Mode Selection ---")
    
    modules = discover_modules()
    
    if not modules:
        print("No scan modules found or loaded.")
        logger.warning("No modules available for selection.")
        return

    while True:
        print("\nAvailable Modules:")
        module_list = list(modules.keys())
        for i, mod_name in enumerate(module_list, 1):
            print(f"{i}. {mod_name}")
        
        print("0. Exit")
        
        choice = input("\nSelect a mode (number): ").strip()
        
        if choice == '0':
            print("Exiting CyberDeck...")
            logger.info("User requested exit.")
            break
            
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(module_list):
                selected_module_name = module_list[choice_idx]
                selected_module = modules[selected_module_name]
                
                print(f"\n[*] Starting module: {selected_module_name}...")
                logger.info(f"Starting module: {selected_module_name}")
                
                # Execute the contract run(config)
                try:
                    result = selected_module.run(config)
                    # Validate the result contract implicitly by trying to save it
                    if isinstance(result, dict) and 'module' in result and 'status' in result:
                        saved_path = save_result(result, config.get("system", {}).get("results_dir", "results"))
                        if saved_path:
                            print(f"[+] Scan complete. Result saved to: {saved_path}")
                        else:
                            print("[-] Scan complete, but failed to save result.")
                    else:
                        logger.error(f"Module '{selected_module_name}' returned an invalid result format: {result}")
                        print("[-] Module execution completed, but returned an invalid result format.")
                except Exception as e:
                    logger.error(f"Error during execution of '{selected_module_name}': {e}")
                    print(f"[-] Module execution failed: {e}")
                    
            else:
                print("Invalid selection. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number.")
