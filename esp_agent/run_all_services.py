import sys
from pathlib import Path

# Forward to root run_all_services.py
ROOT_RUNNER = Path(__file__).resolve().parent.parent / "run_all_services.py"
if str(ROOT_RUNNER.parent) not in sys.path:
    sys.path.insert(0, str(ROOT_RUNNER.parent))

if __name__ == "__main__":
    import run_all_services
    run_all_services.main()
