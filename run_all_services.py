"""
ESP APM Platform — Unified Database & Infrastructure Service Orchestrator
==========================================================================
Single runner script to check, launch, and health-monitor all database storage
services, backend servers, and AI runtime engines required for the platform.

Services managed / monitored:
  [Tier 1: Embedded / File-Based Databases — Always Live]
    1. Telemetry DB (SQLite)      : cced_esp/data/unlabelled.db (2.68M+ records)
    2. Event Store (SQLite)       : esp_agent/esp_events.db
    3. Asset Context Cache (JSON) : cced_esp/data/advait/asset_context_initial_seed_v2_rich.json
    4. Knowledge Graph File (JSON): esp_agent/knowledge_bases/esp/graph/esp_graph.json
    5. Document Knowledge Base    : esp_agent/knowledge_bases/esp/documents/*.txt, *.pdf

  [Tier 2: Containerized Database Services (via docker-compose)]
    6. Neo4j Graph DB             : bolt://localhost:7687  (HTTP: http://localhost:7474)
    7. PostgreSQL / pgvector      : postgresql://localhost:5432/esp_agent
    8. Qdrant Vector Store        : http://localhost:6333
    9. Redis Streams & Cache      : redis://localhost:6379

  [Tier 3: Platform Application & AI Servers]
   10. Local LLM Server           : http://localhost:8080/v1 (llama.cpp / Qwen)
   11. cced_esp Backend REST      : http://127.0.0.1:8000 (FastAPI + Historian API)
   12. esp_agent Gateway          : http://127.0.0.1:8090 (FastAPI + LangGraph BFF)

Usage:
  python run_all_services.py --status         # Check health of all services & DBs
  python run_all_services.py --start-dbs      # Start Docker containers (Neo4j, Postgres, etc.)
  python run_all_services.py --start-all      # Start Docker DBs + Backend + Gateway
  python run_all_services.py --stop-dbs       # Stop Docker DB containers
"""

import sys
import os
import time
import socket
import sqlite3
import urllib.request
import urllib.error
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Path setup
ROOT_DIR = Path(__file__).resolve().parent
ESP_AGENT_DIR = ROOT_DIR / "esp_agent"
CCED_ESP_DIR = ROOT_DIR / "cced_esp"
DOCKER_COMPOSE_FILE = ESP_AGENT_DIR / "docker-compose.yml"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is open and listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_http_url(url: str, timeout: float = 1.5) -> Tuple[bool, str]:
    """Check if an HTTP endpoint returns a valid response."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ESP-Service-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.status in (200, 204, 301, 302, 401, 403), f"HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        # HTTP 401/403 means the server is running but requires auth (e.g. Neo4j)
        return (True, f"HTTP {e.code} (Auth/Endpoint active)")
    except Exception as ex:
        return (False, f"Unreachable ({type(ex).__name__})")


def check_sqlite_db(path: Path) -> Tuple[bool, str]:
    """Check if a SQLite DB exists, is readable, and get table row counts."""
    if not path.exists():
        return (False, "File not found")
    try:
        conn = sqlite3.connect(str(path))
        c = conn.cursor()
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        total_rows = 0
        details = []
        for t in tables[:3]:
            count = c.execute(f"SELECT COUNT(*) FROM \"{t}\";").fetchone()[0]
            total_rows += count
            details.append(f"{t}:{count:,}")
        conn.close()
        return (True, f"{total_rows:,} rows across {len(tables)} tables ({', '.join(details)})")
    except Exception as ex:
        return (False, f"Read error ({ex})")


def check_docker_available() -> bool:
    """Check if docker CLI is present and responsive."""
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        return res.returncode == 0
    except Exception:
        return False


def get_full_health_matrix() -> Dict[str, Dict[str, Any]]:
    """Probe all services and compile a status dictionary."""
    results = {}

    # ── Tier 1: Embedded / File Databases ────────────────────────────────
    hist_db = CCED_ESP_DIR / "data" / "unlabelled.db"
    ok, msg = check_sqlite_db(hist_db)
    results["Telemetry DB (SQLite)"] = {
        "tier": "Tier 1 (File)",
        "live": ok,
        "type": "SQLite",
        "detail": msg,
        "uri": f"file:///{hist_db.as_posix()}",
    }

    events_db = ESP_AGENT_DIR / "esp_events.db"
    ok, msg = check_sqlite_db(events_db)
    results["Event Store (SQLite)"] = {
        "tier": "Tier 1 (File)",
        "live": ok,
        "type": "SQLite",
        "detail": msg,
        "uri": f"file:///{events_db.as_posix()}",
    }

    asset_seed_candidates = [
        ROOT_DIR / "data" / "advait" / "asset_context_initial_seed_v2_rich.json",
        CCED_ESP_DIR / "data" / "advait" / "asset_context_initial_seed_v2_rich.json",
        ROOT_DIR / "data" / "advait" / "advait_api_mock_service" / "data" / "asset_context_initial_seed_v2_rich.json",
    ]
    asset_seed = next((p for p in asset_seed_candidates if p.exists()), asset_seed_candidates[0])
    results["Asset Registry (Cache)"] = {
        "tier": "Tier 1 (File)",
        "live": asset_seed.exists(),
        "type": "JSON Cache",
        "detail": f"{asset_seed.stat().st_size:,} bytes" if asset_seed.exists() else "Missing",
        "uri": f"file:///{asset_seed.as_posix()}",
    }

    kg_json = ESP_AGENT_DIR / "knowledge_bases" / "esp" / "graph" / "esp_graph.json"
    results["Knowledge Graph (File)"] = {
        "tier": "Tier 1 (File)",
        "live": kg_json.exists(),
        "type": "JSON Graph",
        "detail": f"{kg_json.stat().st_size:,} bytes" if kg_json.exists() else "Missing",
        "uri": f"file:///{kg_json.as_posix()}",
    }

    # ── Tier 2: Containerized Database Services ──────────────────────────
    neo4j_live = check_tcp_port("localhost", 7687)
    results["Neo4j Graph Database"] = {
        "tier": "Tier 2 (Docker)",
        "live": neo4j_live,
        "type": "Graph DB",
        "detail": "Port 7687 open (Bolt protocol)" if neo4j_live else "Port 7687 closed (run docker-compose up)",
        "uri": "bolt://localhost:7687" if neo4j_live else "FALLBACK: esp_graph.json",
    }

    pg_live = check_tcp_port("localhost", 5432)
    results["PostgreSQL / pgvector"] = {
        "tier": "Tier 2 (Docker)",
        "live": pg_live,
        "type": "Relational + Vector",
        "detail": "Port 5432 open" if pg_live else "Port 5432 closed (run docker-compose up)",
        "uri": "postgresql://postgres:postgres@localhost:5432/esp_agent" if pg_live else "FALLBACK: local chunk search",
    }

    qdrant_ok, qdrant_msg = check_http_url("http://localhost:6333/readyz")
    results["Qdrant Vector DB"] = {
        "tier": "Tier 2 (Docker)",
        "live": qdrant_ok or check_tcp_port("localhost", 6333),
        "type": "Vector DB",
        "detail": qdrant_msg if qdrant_ok else "Port 6333 closed",
        "uri": "http://localhost:6333" if qdrant_ok else "OFFLINE",
    }

    redis_live = check_tcp_port("localhost", 6379)
    results["Redis Cache / Streams"] = {
        "tier": "Tier 2 (Docker)",
        "live": redis_live,
        "type": "In-Memory KV",
        "detail": "Port 6379 open" if redis_live else "Port 6379 closed",
        "uri": "redis://localhost:6379" if redis_live else "OFFLINE",
    }

    # ── Tier 3: Applications & AI Runtime ────────────────────────────────
    env_file = ESP_AGENT_DIR / ".env"
    llm_base = "http://localhost:8080/v1"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as ef:
                for line in ef:
                    if line.strip().startswith("LLM_GATEWAY_URL="):
                        llm_base = line.strip().split("=", 1)[1].strip()
        except Exception:
            pass
    llm_base = os.getenv("LLM_GATEWAY_URL", llm_base)

    llm_models_url = f"{llm_base}/models"
    llm_ok, llm_msg = check_http_url(llm_models_url)
    results["LLM Server (llama.cpp)"] = {
        "tier": "Tier 3 (App/AI)",
        "live": llm_ok,
        "type": "LLM Inference",
        "detail": llm_msg if llm_ok else f"Unreachable at {llm_base}",
        "uri": llm_base if llm_ok else "MOCK FALLBACK",
    }

    backend_ok, backend_msg = check_http_url("http://127.0.0.1:8000/docs")
    results["cced_esp Backend REST"] = {
        "tier": "Tier 3 (App/AI)",
        "live": backend_ok or check_tcp_port("127.0.0.1", 8000),
        "type": "FastAPI :8000",
        "detail": backend_msg if backend_ok else ("Port 8000 open" if check_tcp_port("127.0.0.1", 8000) else "Port 8000 closed (optional, SQLite fallback active)"),
        "uri": "http://127.0.0.1:8000/api/v1/historian" if backend_ok else "FALLBACK: Direct SQLite in-process",
    }

    gateway_ok, gateway_msg = check_http_url("http://127.0.0.1:8090/docs")
    results["esp_agent Gateway BFF"] = {
        "tier": "Tier 3 (App/AI)",
        "live": gateway_ok or check_tcp_port("127.0.0.1", 8090),
        "type": "FastAPI :8090",
        "detail": gateway_msg if gateway_ok else ("Port 8090 open" if check_tcp_port("127.0.0.1", 8090) else "Port 8090 closed (run run_agent_server.py)"),
        "uri": "http://127.0.0.1:8090" if gateway_ok else "OFFLINE",
    }

    return results


def print_health_matrix(matrix: Dict[str, Dict[str, Any]]):
    SEP = "=" * 88
    sep = "-" * 88
    print(SEP)
    print(" ESP APM PLATFORM — UNIFIED DATABASE & INFRASTRUCTURE HEALTH MATRIX")
    print(SEP)
    print(f" {'Service / Database':<32} {'Status':<10} {'Tier':<16} {'Evidence Deep-Link / Target URI'}")
    print(f" {'-'*32} {'-'*10} {'-'*16} {'-'*26}")

    for name, info in matrix.items():
        status_icon = "🟢 LIVE" if info["live"] else "⚪ OFFLINE"
        print(f" {name:<32} {status_icon:<10} {info['tier']:<16} {info['uri']}")
        print(f"   ↳ Details: {info['detail']}")

    print(sep)
    docker_status = "🟢 Available" if check_docker_available() else "⚪ Not running / Not installed"
    print(f" Docker Engine Status: {docker_status}")
    print(SEP)


def start_docker_services():
    """Start Neo4j, PostgreSQL, Qdrant, Redis via docker-compose."""
    if not check_docker_available():
        print("❌ Error: Docker is not running or not installed. Cannot start containerized DBs.")
        print("   Please start Docker Desktop and rerun: python run_all_services.py --start-dbs")
        return False

    if not DOCKER_COMPOSE_FILE.exists():
        print(f"❌ Error: {DOCKER_COMPOSE_FILE} not found.")
        return False

    print(f"🚀 Starting Docker DB containers (Neo4j, Postgres, Qdrant, Redis)...")
    cmd = ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d"]
    res = subprocess.run(cmd, cwd=str(ESP_AGENT_DIR))
    if res.returncode == 0:
        print("✅ Docker DB services launched in background.")
        print("   Waiting 5 seconds for initialization...")
        time.sleep(5)
        print_health_matrix(get_full_health_matrix())
        return True
    else:
        print(f"❌ docker compose returned exit code {res.returncode}")
        return False


def stop_docker_services():
    """Stop Docker containers."""
    if not check_docker_available():
        print("Docker not available.")
        return
    print(f"🛑 Stopping Docker DB containers...")
    subprocess.run(["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "down"], cwd=str(ESP_AGENT_DIR))
    print("✅ Stopped.")


def main():
    ap = argparse.ArgumentParser(description="ESP APM Database & Infrastructure Service Orchestrator")
    ap.add_argument("--status", action="store_true", help="Print health status matrix of all services")
    ap.add_argument("--start-dbs", action="store_true", help="Start Docker container DBs (Neo4j, Postgres, Qdrant, Redis)")
    ap.add_argument("--stop-dbs", action="store_true", help="Stop Docker container DBs")
    ap.add_argument("--start-all", action="store_true", help="Start Docker DBs and show full status")
    args = ap.parse_args()

    if args.start_dbs or args.start_all:
        start_docker_services()
    elif args.stop_dbs:
        stop_docker_services()
    else:
        # Default action is to show health status
        print_health_matrix(get_full_health_matrix())


if __name__ == "__main__":
    main()
