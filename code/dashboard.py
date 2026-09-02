"""
CCED VFD EDA Dashboard Forwarder
================================
Points to the actual dashboard located in eda/dashboard.py.
"""
import os
import runpy

if __name__ == "__main__":
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eda", "dashboard.py")
    runpy.run_path(target_path, run_name="__main__")
