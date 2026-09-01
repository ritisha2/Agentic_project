"""
Neo4j Knowledge Graph Seeder
Grounded in ESP APM Phase 3 & Phase 8 Knowledge Graph architecture.
Loads nodes and relationships from esp_graph.json into live Neo4j database (bolt://localhost:7687).
"""

import os
import json
import logging
from pathlib import Path
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
KG_JSON_PATH = ROOT_DIR / "knowledge_bases" / "esp" / "graph" / "esp_graph.json"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


def seed_neo4j_graph():
    if not KG_JSON_PATH.exists():
        print(f"[-] KG JSON file not found at: {KG_JSON_PATH}")
        return False

    with open(KG_JSON_PATH, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    print(f"[*] Connecting to Neo4j at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # 1. Clear existing graph or ensure uniqueness constraints
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component) REQUIRE c.name IS UNIQUE;")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Subsystem) REQUIRE s.name IS UNIQUE;")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:FailureMode) REQUIRE f.name IS UNIQUE;")

            # 2. Seed Subsystems
            subsystems = graph_data.get("subsystems", [])
            for sub in subsystems:
                name = sub if isinstance(sub, str) else sub.get("name")
                session.run("MERGE (s:Subsystem {name: $name})", name=name)
            print(f"[+] Loaded {len(subsystems)} Subsystems into Neo4j.")

            # 3. Seed Components
            components = graph_data.get("components", [])
            for comp in components:
                name = comp if isinstance(comp, str) else comp.get("name")
                subsystem = comp.get("subsystem", "Motor Section") if isinstance(comp, dict) else "Motor Section"
                session.run("""
                    MERGE (c:Component {name: $name})
                    MERGE (s:Subsystem {name: $subsystem})
                    MERGE (c)-[:PART_OF]->(s)
                """, name=name, subsystem=subsystem)
            print(f"[+] Loaded {len(components)} Components with PART_OF relations into Neo4j.")

            # 4. Seed Failure Modes
            failure_modes = graph_data.get("failure_modes", [])
            for fm in failure_modes:
                name = fm if isinstance(fm, str) else fm.get("name")
                session.run("MERGE (f:FailureMode {name: $name})", name=name)
            print(f"[+] Loaded {len(failure_modes)} Failure Modes into Neo4j.")

            # 5. Seed Relationships (Causes, Symptoms, Indicators)
            relationships = graph_data.get("relationships", [])
            for rel in relationships:
                src = rel.get("source", "")
                tgt = rel.get("target", "")
                rel_type = rel.get("type", "CAUSES").upper().replace(" ", "_")
                session.run(f"""
                    MERGE (a {{name: $src}})
                    MERGE (b {{name: $tgt}})
                    MERGE (a)-[r:{rel_type}]->(b)
                """, src=src, tgt=tgt)
            print(f"[+] Loaded {len(relationships)} Relationships into Neo4j.")

        driver.close()
        print("[+] Neo4j Knowledge Graph successfully seeded from esp_graph.json!")
        return True
    except Exception as ex:
        print(f"[-] Neo4j seeding error: {ex}")
        return False


if __name__ == "__main__":
    seed_neo4j_graph()
