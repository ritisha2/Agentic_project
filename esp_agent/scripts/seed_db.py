"""
Database Seeding Script for ESP Knowledge Base
Loads document manifests, fault taxonomy, alert playbooks, glossary, and objectives into PostgreSQL tables.
"""

import os
import glob
import json
import yaml
import psycopg2

DB_CONFIG = {
    "dbname": "esp_agent",
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432"))
}

ROOT_DIR = r"x:\TAS\Agentic_project"
MANIFESTS_DIR = os.path.join(ROOT_DIR, "esp-knowledge", "sources", "manifests")
DETERMINISTIC_DIR = os.path.join(ROOT_DIR, "esp-knowledge", "deterministic")

def seed_documents(conn):
    """Seed documents table from JSON manifests"""
    cur = conn.cursor()
    manifest_files = glob.glob(os.path.join(MANIFESTS_DIR, "*.json"))
    count = 0
    for mf in manifest_files:
        with open(mf, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        cur.execute("""
            INSERT INTO documents (
                document_id, title, canonical_category, doc_type,
                author_publisher, publication_year, source_filename,
                standardized_filename, file_path, file_size_bytes,
                sha256_checksum, total_pages, extracted_char_count, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                status = EXCLUDED.status;
        """, (
            data.get("document_id"),
            data.get("title"),
            data.get("canonical_category"),
            data.get("doc_type"),
            data.get("author_publisher"),
            str(data.get("publication_year", "")),
            data.get("source_filename"),
            data.get("standardized_filename"),
            data.get("file_path"),
            data.get("file_size_bytes", 0),
            data.get("sha256_checksum", f"hash-{data.get('document_id')}"),
            data.get("total_pages", 0),
            data.get("extracted_char_count", 0),
            data.get("status", "PARSED_AND_NORMALIZED")
        ))
        count += 1
    conn.commit()
    cur.close()
    print(f"[+] Loaded {count} document manifest records into 'documents' table.")

def seed_faults(conn):
    """Seed fault_patterns table from YAML"""
    fault_file = os.path.join(DETERMINISTIC_DIR, "faults", "seed_faults.yaml")
    if not os.path.exists(fault_file):
        return
    with open(fault_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    cur = conn.cursor()
    count = 0
    for fault in data.get("faults", []):
        cur.execute("""
            INSERT INTO fault_patterns (
                fault_id, category, preferred_name, synonyms,
                canonical_metric, symptoms, contributing_factors,
                evidence_required, severity_range, escalation, source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fault_id) DO UPDATE SET
                preferred_name = EXCLUDED.preferred_name,
                category = EXCLUDED.category;
        """, (
            fault["fault_id"],
            fault["category"],
            fault["preferred_name"],
            json.dumps(fault.get("synonyms", [])),
            fault.get("canonical_metric"),
            json.dumps(fault.get("symptoms", [])),
            json.dumps(fault.get("contributing_factors", [])),
            json.dumps(fault.get("evidence_required", [])),
            fault.get("severity_range"),
            fault.get("escalation"),
            fault.get("source")
        ))
        count += 1
    conn.commit()
    cur.close()
    print(f"[+] Loaded {count} fault records into 'fault_patterns' table.")

def seed_glossary(conn):
    """Seed glossary_terms table from YAML"""
    glossary_file = os.path.join(DETERMINISTIC_DIR, "glossary", "seed_glossary.yaml")
    if not os.path.exists(glossary_file):
        return
    with open(glossary_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    cur = conn.cursor()
    count = 0
    for item in data.get("terms", []):
        cur.execute("""
            INSERT INTO glossary_terms (
                term_id, preferred_term, synonyms, definition, domain, unit
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (term_id) DO UPDATE SET
                definition = EXCLUDED.definition;
        """, (
            item["term_id"],
            item["preferred_name"],
            json.dumps(item.get("synonyms", [])),
            item["definition"].strip(),
            item.get("domain"),
            item.get("unit")
        ))
        count += 1
    conn.commit()
    cur.close()
    print(f"[+] Loaded {count} terms into 'glossary_terms' table.")

def seed_objectives(conn):
    """Seed agent_objectives table from YAML"""
    obj_file = os.path.join(DETERMINISTIC_DIR, "objectives", "seed_objectives.yaml")
    if not os.path.exists(obj_file):
        return
    with open(obj_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    cur = conn.cursor()
    count = 0
    for obj in data.get("objectives", []):
        cur.execute("""
            INSERT INTO agent_objectives (
                objective_id, name, trigger_keywords, description,
                required_tools, optional_tools, success_criteria, safety_policy
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (objective_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description;
        """, (
            obj["objective_id"],
            obj["name"],
            json.dumps(obj.get("trigger_keywords", [])),
            obj.get("description"),
            json.dumps(obj.get("required_tools", [])),
            json.dumps(obj.get("optional_tools", [])),
            obj.get("success_criteria"),
            json.dumps(obj.get("safety_policy", {}))
        ))
        count += 1
    conn.commit()
    cur.close()
    print(f"[+] Loaded {count} objectives into 'agent_objectives' table.")

def seed_phase3_faults(conn):
    """Update pilot fault_patterns rows with Phase 3 structured JSONB pattern fields."""
    cur = conn.cursor()
    # Keyed by existing fault_id values in the DB
    phase3_faults = [
        {
            "fault_id": "PUMP_WEAR",
            "qualitative_patterns": {"flow": "declining", "PDP": "declining", "current": "stable_or_declining"},
            "quantitative_rules": [
                {"metric": "flow_bpd", "op": "<", "threshold_pct_bep": 70, "desc": "Flow below 70% BEP"}
            ],
            "confirmation_checks": [
                "Verify VSD frequency is unchanged",
                "Check PIP is stable (no gas ingestion)",
                "Review trend over 7+ days — gradual decline signature"
            ],
            "contradicting_signals": ["Sudden current spike (suggests stuck pump, not wear)", "PIP drop (suggests gas or restriction)"],
            "approved_actions": ["Log progressive wear in surveillance", "Schedule inspection at next workover"],
            "authority_level": "B"
        },
        {
            "fault_id": "GAS_LOCK",
            "qualitative_patterns": {"current": "oscillating", "flow": "unstable", "PIP": "low_or_variable"},
            "quantitative_rules": [
                {"metric": "pip_psi", "op": "<", "threshold": 300, "desc": "PIP below 300 psi — free gas ingestion risk"}
            ],
            "confirmation_checks": [
                "Correlate current oscillation with production rate oscillation",
                "Check GOR trend (gas-oil ratio rising)",
                "Verify PIP vs bubble point at operating conditions"
            ],
            "contradicting_signals": ["Stable PIP above bubble point (unlikely gas interference)"],
            "approved_actions": ["Reduce frequency to raise PIP above bubble point", "Evaluate gas separator performance"],
            "authority_level": "B"
        },
        {
            "fault_id": "MOTOR_OVERHEATING",
            "qualitative_patterns": {"motor_temperature": "rising", "PIP": "low"},
            "quantitative_rules": [
                {"metric": "motor_temperature_c", "op": ">", "threshold": 130, "desc": "Motor temp > 130°C WARNING"},
                {"metric": "motor_temperature_c", "op": ">", "threshold": 150, "desc": "Motor temp > 150°C CRITICAL"}
            ],
            "confirmation_checks": [
                "Verify low PIP is reducing fluid cooling over motor housing",
                "Check for scale deposition reports",
                "Review BHT baseline vs current operating temperature"
            ],
            "contradicting_signals": ["High PIP with normal fluid flow (thermal issue likely external, not cooling deficit)"],
            "approved_actions": ["Reduce operating frequency to increase PIP", "Alert engineering if > 130°C sustained"],
            "authority_level": "B"
        },
        {
            "fault_id": "BEARING_WEAR",
            "qualitative_patterns": {"vibration": "high_radial", "axial_vibration": "spiking"},
            "quantitative_rules": [
                {"metric": "radial_vibration_g", "op": ">", "threshold": 3.0, "desc": "Radial vibration > 3.0g WARNING"},
                {"metric": "axial_vibration_g", "op": ">", "threshold": 1.5, "desc": "Axial vibration > 1.5g WARNING"}
            ],
            "confirmation_checks": [
                "Review vibration spectrum for sub-synchronous frequencies",
                "Check operation vs ROR (operating outside range increases wear)",
                "Correlate with solids/sand production reports"
            ],
            "contradicting_signals": ["Vibration spike only at startup then normalizes (rotor unbalance, not bearing wear)"],
            "approved_actions": ["Operate within ROR", "Flag for next intervention planning"],
            "authority_level": "B"
        },
        {
            "fault_id": "SCALE_DEPOSITION",
            "qualitative_patterns": {"flow": "very_slowly_declining", "motor_temperature": "gradually_rising", "current": "stable_or_slightly_rising"},
            "quantitative_rules": [
                {"metric": "motor_temperature_c", "op": ">", "threshold": 120, "desc": "Sustained temp rise with stable current — scale-insulated motor housing"}
            ],
            "confirmation_checks": [
                "Check produced water chemistry (high Ca/Mg/Ba scale indices)",
                "Review CTF/inhibitor injection records",
                "Compare current vs initial motor temperature at same flow rate"
            ],
            "contradicting_signals": ["Low PIP (gas-driven temperature issue, not scale)", "Sudden temperature spike (gas influx or electrical fault)"],
            "approved_actions": ["Review chemical inhibition program", "Log in asset integrity record for next intervention"],
            "authority_level": "B"
        },
    ]

    updated = 0
    for f in phase3_faults:
        cur.execute("""
            UPDATE fault_patterns SET
                qualitative_patterns = %s,
                quantitative_rules = %s,
                confirmation_checks = %s,
                contradicting_signals = %s,
                approved_actions = %s,
                authority_level = %s
            WHERE fault_id = %s;
        """, (
            json.dumps(f["qualitative_patterns"]),
            json.dumps(f["quantitative_rules"]),
            json.dumps(f["confirmation_checks"]),
            json.dumps(f["contradicting_signals"]),
            json.dumps(f["approved_actions"]),
            f["authority_level"],
            f["fault_id"]
        ))
        updated += cur.rowcount
    conn.commit()
    cur.close()
    print(f"[+] Updated {updated} fault_patterns with Phase 3 structured fields.")


def seed_historical_cases(conn):
    """Seed pilot historical case library (Sprint 3.7)"""
    cur = conn.cursor()
    cases = [
        {
            "case_id": "CASE-2024-001",
            "asset_id": "ESP-Well-Pilot-01",
            "well_id": "WELL-P01",
            "equipment_model": "Weatherford DN1750",
            "event_time": "2024-03-15 14:30:00",
            "symptom_summary": "Gradual flow decline over 14 days with stable current and PIP — worn pump suspected",
            "telemetry_signature": {"flow_bpd_trend": "declining_14d", "motor_current": "stable", "pip_psi": "stable_350"},
            "event_sequence": ["Day 1: Flow 1750 bpd", "Day 7: Flow 1550 bpd", "Day 14: Flow 1200 bpd — pulled for inspection"],
            "confirmed_cause": "WORN_PUMP",
            "candidate_causes": ["WORN_PUMP", "TUBING_LEAK"],
            "operator_action": "Workover initiated; pump pulled and inspected",
            "action_outcome": "Stage wear confirmed; replacement pump installed; flow restored to 1780 bpd",
            "production_impact": "550 bpd deferred over 14 days",
            "source_reports": ["RCA-2024-P01-003", "WO-2024-P01-007"],
            "approval_status": "APPROVED"
        },
        {
            "case_id": "CASE-2024-002",
            "asset_id": "ESP-Well-Pilot-02",
            "well_id": "WELL-P02",
            "equipment_model": "Baker Hughes GN4000",
            "event_time": "2024-06-08 09:15:00",
            "symptom_summary": "Current oscillation and unstable flow with PIP at 280 psi — gas interference confirmed",
            "telemetry_signature": {"pip_psi": 280, "current_amps_cv": 0.18, "flow_bpd_cv": 0.22},
            "event_sequence": ["Hour 0: PIP drops below 300 psi", "Hour 2: Current oscillations begin", "Hour 4: Operator reduces frequency from 60 to 52 Hz", "Hour 6: PIP recovers to 320 psi, oscillations cease"],
            "confirmed_cause": "GAS_INTERFERENCE",
            "candidate_causes": ["GAS_INTERFERENCE", "WORN_PUMP"],
            "operator_action": "Reduced VSD frequency to 52 Hz to raise PIP above bubble point",
            "action_outcome": "Stabilized at 52 Hz; flow 1420 bpd stable; no further oscillations",
            "production_impact": "80 bpd deferred (frequency reduction)",
            "source_reports": ["SURV-2024-P02-041"],
            "approval_status": "APPROVED"
        }
    ]

    inserted = 0
    for c in cases:
        cur.execute("""
            INSERT INTO historical_cases (
                case_id, asset_id, well_id, equipment_model, event_time,
                symptom_summary, telemetry_signature, event_sequence,
                confirmed_cause, candidate_causes, operator_action, action_outcome,
                production_impact, source_reports, approval_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (case_id) DO UPDATE SET
                confirmed_cause = EXCLUDED.confirmed_cause,
                approval_status = EXCLUDED.approval_status;
        """, (
            c["case_id"], c["asset_id"], c["well_id"], c["equipment_model"], c["event_time"],
            c["symptom_summary"], json.dumps(c["telemetry_signature"]), json.dumps(c["event_sequence"]),
            c["confirmed_cause"], json.dumps(c["candidate_causes"]), c["operator_action"],
            c["action_outcome"], c["production_impact"], json.dumps(c["source_reports"]), c["approval_status"]
        ))
        inserted += 1
    conn.commit()
    cur.close()
    print(f"[+] Seeded {inserted} historical cases into 'historical_cases' table.")


def seed_pump_curves(conn):
    """Seed pilot pump curve reference (Sprint 3.8)"""
    cur = conn.cursor()
    curves = [
        {
            "curve_id": "CURVE-WF-DN1750-60HZ",
            "pump_model": "Weatherford DN1750",
            "manufacturer": "Weatherford",
            "stage_count": 40,
            "frequency_hz": 60.0,
            "ror_min_bpd": 1400.0,
            "ror_max_bpd": 2100.0,
            "bep_bpd": 1750.0,
            "curve_points": [
                {"flow_bpd": 1400, "head_ft_per_stage": 46.2, "efficiency_pct": 62},
                {"flow_bpd": 1600, "head_ft_per_stage": 44.8, "efficiency_pct": 68},
                {"flow_bpd": 1750, "head_ft_per_stage": 42.3, "efficiency_pct": 71},
                {"flow_bpd": 1900, "head_ft_per_stage": 39.1, "efficiency_pct": 67},
                {"flow_bpd": 2100, "head_ft_per_stage": 33.5, "efficiency_pct": 58},
            ],
            "authority_level": "B"
        }
    ]

    inserted = 0
    for c in curves:
        cur.execute("""
            INSERT INTO pump_curves (
                curve_id, pump_model, manufacturer, stage_count, frequency_hz,
                ror_min_bpd, ror_max_bpd, bep_bpd, curve_points, authority_level
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (curve_id) DO UPDATE SET
                curve_points = EXCLUDED.curve_points,
                bep_bpd = EXCLUDED.bep_bpd;
        """, (
            c["curve_id"], c["pump_model"], c["manufacturer"], c["stage_count"],
            c["frequency_hz"], c["ror_min_bpd"], c["ror_max_bpd"], c["bep_bpd"],
            json.dumps(c["curve_points"]), c["authority_level"]
        ))
        inserted += 1
    conn.commit()
    cur.close()
    print(f"[+] Seeded {inserted} pump curves into 'pump_curves' table.")


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    print(f"[*] Seeding database '{DB_CONFIG['dbname']}'...")
    seed_documents(conn)
    seed_faults(conn)
    seed_glossary(conn)
    seed_objectives(conn)
    seed_phase3_faults(conn)
    seed_historical_cases(conn)
    seed_pump_curves(conn)
    conn.close()
    print("[+] Database seeding completed successfully!")

if __name__ == "__main__":
    main()
