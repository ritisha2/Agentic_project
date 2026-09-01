"""
Root forwarder to run esp_agent/run_full_query_pipeline.py from project root.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ESP_AGENT_DIR = ROOT / "esp_agent"

if str(ESP_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(ESP_AGENT_DIR))

if __name__ == "__main__":
    import run_full_query_pipeline
    run_full_query_pipeline.main()
