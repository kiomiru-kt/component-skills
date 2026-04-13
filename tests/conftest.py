import importlib.util
import sys
from pathlib import Path


def _load_script():
    script_path = Path(__file__).parent.parent / "scripts" / "figma-tokenize.py"
    spec = importlib.util.spec_from_file_location("figma_tokenize", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


figma_tokenize = _load_script()
sys.modules["figma_tokenize"] = figma_tokenize
