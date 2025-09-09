import os
from dotenv import load_dotenv

load_dotenv()

def _get_env_var(name):
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f'Missing required environment variable: {name}')
    return val

# Main directory and explicit paths
PARENT_DIR = _get_env_var('PARENT_DIR')
LOGGING_PATH = os.path.join(PARENT_DIR, _get_env_var('LOGGING_FLDR'))

