from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = Path(os.getenv("ASSET_DATA_FILE", BASE_DIR/"data"/"asset_context_initial_seed_v2_rich.json"))
