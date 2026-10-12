# Synapse AI Backend Package
import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load environment variables from backend/.env or project root
_curr_dir = Path(__file__).resolve().parent
_backend_env = _curr_dir.parent / ".env"
_root_env = _curr_dir.parent.parent / ".env"

if _backend_env.exists():
    load_dotenv(_backend_env)
elif _root_env.exists():
    load_dotenv(_root_env)
else:
    load_dotenv()
