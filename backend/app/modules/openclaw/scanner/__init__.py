"""OpenClaw sub-package."""
import os
import importlib
import inspect
import logging

logger = logging.getLogger(__name__)

# Registry of all available agent classes in the scanner module
AGENT_REGISTRY = {}

def discover_agents():
    """Auto-discover and register all scanner agent functions/classes."""
    global AGENT_REGISTRY
    scanner_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(scanner_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"app.modules.openclaw.scanner.{module_name}")
                
                # Look for async publishers
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) and name.startswith("async_") and name.endswith("_publisher"):
                        AGENT_REGISTRY[name] = obj
                        logger.debug(f"Registered agent function: {name} from {module_name}")
                    
                    # Also register class-based agents if needed
                    elif inspect.isclass(obj) and (name.endswith("Agent") or name.endswith("Scanner")):
                        AGENT_REGISTRY[name] = obj
                        logger.debug(f"Registered agent class: {name} from {module_name}")
                        
            except ImportError as e:
                logger.error(f"Failed to import scanner module {module_name}: {e}")

# Run discovery on init
discover_agents()
