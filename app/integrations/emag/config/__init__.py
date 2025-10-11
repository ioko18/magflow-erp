import importlib.util
import pathlib
import sys

# Load the sibling config.py (located one directory above this package)
_config_path = pathlib.Path(__file__).resolve().parents[1] / "config.py"
_spec = importlib.util.spec_from_file_location("emag_config", _config_path)
_emag_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_emag_config)
# Optionally register the loaded module for future imports
sys.modules[__name__ + ".config_module"] = _emag_config

# Re-export required symbols from the loaded config module
EmagAccountType = _emag_config.EmagAccountType
EmagEnvironment = _emag_config.EmagEnvironment
EmagSettings = _emag_config.EmagSettings
get_settings = _emag_config.get_settings
settings = _emag_config.settings

__all__ = [
    "EmagAccountType",
    "EmagEnvironment",
    "EmagSettings",
    "get_settings",
    "settings",
]
