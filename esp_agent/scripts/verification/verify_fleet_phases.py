"""
Multi-Fleet Phases Verification Script
========================================
Verifies all 6 fleet-scoped objectives (OP08-OP13) are correctly registered,
routed, and executable. Tests routing confidence, required tools, specialist
configuration, and RBAC safety gates.

Fleet Objectives Under Test:
- OP08: Fleet Asset Inventory & Counts
- OP09: Fleet Production Optimization & Headroom Ranking  
- OP10: Fleet Design Sizing & Operating Envelope Audit
- OP11: Fleet Maintenance Priority & RUL Urgency Ranking
- OP12: Cross-Asset Case Similarity & Failure Clustering
- OP13: Fleet Executive Performance & Health Summary

Usage:
    python verify_fleet_phases.py
    python verify_fleet_phases.py --verbose
    python verify_fleet_phases.py --objective OP08  # Test single objective
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# Ensure project root in path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.agent.objective_registry import ObjectiveRegistry
from src.agent.intent_router import IntentRouter

# ANSI colors for terminal output (ASCII-safe for Windows cp1252)
PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"
BOLD = ""
RESET = ""


FLEET_OBJECTIVES = {
    "OP08_FLEET_INVENTORY": {
        "title": "Fleet Asset Inventory & Counts",
        "test_queries": [
            "list all assets",
            "how many wells do we have",
            "fleet inventory",
            "show me all assets in the field",
            "count of assets"
        ],
        "required_tools": ["list_fleet_assets"],
        "scope": "fleet",
        "strategic_objectives": ["O1"]
    },
    "OP09_FLEET_PRODUCTION_OPTIMIZATION": {
        "title": "Fleet Production Optimization & Headroom Ranking",
        "test_queries": [
            "optimize fleet production",
            "which wells have the most upside",
            "rank fleet by production headroom",
            "fleet optimization opportunities",
            "production upside across fleet"
        ],
        "required_tools": ["list_fleet_assets", "simulate_frequency_change", "calculate_tdh"],
        "scope": "fleet",
        "strategic_objectives": ["O1", "O5"]
    },
    "OP10_FLEET_DESIGN_SIZING": {
        "title": "Fleet Design Sizing & Operating Envelope Audit",
        "test_queries": [
            "fleet sizing audit",
            "which wells are outside BEP",
            "envelope audit across fleet",
            "upthrust risk in the field",
            "fleet design check"
        ],
        "required_tools": ["list_fleet_assets", "calculate_tdh"],
        "scope": "fleet",
        "strategic_objectives": ["O1", "O2"]
    },
    "OP11_FLEET_MAINTENANCE_PRIORITY": {
        "title": "Fleet Maintenance Priority & RUL Urgency Ranking",
        "test_queries": [
            "rank fleet maintenance urgency",
            "which wells need workover",
            "fleet health ranking",
            "priority workovers",
            "hottest wells in fleet"
        ],
        "required_tools": ["list_fleet_assets", "get_model_output"],
        "scope": "fleet",
        "strategic_objectives": ["O2", "O4"]
    },
    "OP12_FLEET_CASE_ANALYTICS": {
        "title": "Cross-Asset Case Similarity & Failure Clustering",
        "test_queries": [
            "recurring failure clusters",
            "fleet case similarity",
            "similar trips across fleet",
            "cluster failure patterns",
            "fleet incident history"
        ],
        "required_tools": ["list_fleet_assets", "search_knowledge"],
        "scope": "fleet",
        "strategic_objectives": ["O3", "O5"]
    },
    "OP13_FLEET_EXECUTIVE_REPORTING": {
        "title": "Fleet Executive Performance & Health Summary",
        "test_queries": [
            "generate fleet report",
            "executive summary",
            "field performance report",
            "fleet health summary",
            "overall field status"
        ],
        "required_tools": ["list_fleet_assets", "get_model_output"],
        "scope": "fleet",
        "strategic_objectives": ["O1", "O2", "O4"]
    }
}


def hr(title: str = ""):
    """Print horizontal rule with optional title."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print('=' * 80)
    else:
        print('-' * 80)


def test_objective_registration(registry: ObjectiveRegistry, objective_id: str, 
                                 config: Dict, verbose: bool = False) -> bool:
    """
    Phase 1: Verify objective is registered and metadata matches spec.
    """
    hr(f"Phase 1 — Registration Check: {objective_id}")
    
    all_objectives = registry.list_all()
    if objective_id not in [o.objective_id for o in all_objectives]:
        print(f"  {FAIL} Objective {objective_id} not found in registry")
        return False
    
    print(f"  {PASS} Objective {objective_id} is registered")
    
    # Get objective definition
    obj_def = registry.get(objective_id)
    if not obj_def:
        print(f"  {FAIL} Could not retrieve objective definition")
        return False
    
    # Verify scope
    if obj_def.scope != config["scope"]:
        print(f"  {FAIL} Scope mismatch: expected '{config['scope']}', got '{obj_def.scope}'")
        return False
    print(f"  {PASS} Scope correctly set to: {obj_def.scope}")
    
    # Verify required tools
    missing_tools = set(config["required_tools"]) - set(obj_def.required_tools or [])
    if missing_tools:
        print(f"  {FAIL} Missing required tools: {missing_tools}")
        return False
    print(f"  {PASS} Required tools present: {', '.join(config['required_tools'])}")
    
    # Verify strategic objectives mapping
    if not all(so in (obj_def.strategic_objectives or []) for so in config["strategic_objectives"]):
        print(f"  {WARN} Strategic objectives mismatch (non-fatal)")
    else:
        print(f"  {PASS} Strategic objectives: {', '.join(config['strategic_objectives'])}")
    
    if verbose:
        print(f"\n  {INFO} Full definition:")
        print(f"    Title: {obj_def.title}")
        print(f"    Description: {obj_def.description}")
        print(f"    Intent Classes: {len(obj_def.intent_classes or [])} phrases")
        print(f"    Allowed Specialists: {obj_def.allowed_specialists or 'None (fleet-tier)'}")
    
    return True


def test_routing_confidence(router: IntentRouter, objective_id: str, 
                            config: Dict, verbose: bool = False) -> bool:
    """
    Phase 2: Test routing for all query variants and verify confidence thresholds.
    """
    hr(f"Phase 2 — Intent Routing: {objective_id}")
    
    results = []
    for query in config["test_queries"]:
        routed_id, confidence, path = router.route(query)
        match = routed_id == objective_id
        results.append((query, routed_id, confidence, path, match))
        
        status = PASS if match else FAIL
        conf_str = f"{confidence:.2f}"
        
        if match:
            if confidence >= 0.90:
                conf_marker = f"{conf_str} (HIGH)"
            elif confidence >= 0.75:
                conf_marker = f"{conf_str} (MED)"
            else:
                conf_marker = f"{conf_str} (LOW)"
        else:
            conf_marker = f"{conf_str} (MISS)"
        
        if verbose or not match:
            print(f"  {status} '{query}'")
            print(f"      → {routed_id} (conf={conf_marker}, path={path})")
    
    match_count = sum(1 for _, _, _, _, match in results if match)
    total = len(results)
    success_rate = (match_count / total) * 100
    
    print(f"\n  Match Rate: {match_count}/{total} ({success_rate:.0f}%)")
    
    if match_count == total:
        print(f"  {PASS} All queries routed correctly")
        return True
    elif match_count >= total * 0.8:
        print(f"  {WARN} Most queries routed correctly (≥80%)")
        return True
    else:
        print(f"  {FAIL} Routing accuracy below threshold (<80%)")
        return False


def test_safety_constraints(registry: ObjectiveRegistry, objective_id: str, 
                           verbose: bool = False) -> bool:
    """
    Phase 3: Verify RBAC safety gates and forbidden actions.
    """
    hr(f"Phase 3 — Safety Constraints: {objective_id}")
    
    obj_def = registry.get(objective_id)
    safety = obj_def.safety
    
    # Fleet objectives should always be advisory_only
    if not safety or not safety.advisory_only:
        print(f"  [FAIL] Fleet objective missing 'advisory_only: true' safety flag")
        return False
    print(f"  [PASS] Advisory-only mode enforced")
    
    # Check for forbidden actions (OP09 has fleet frequency override restriction)
    forbidden = safety.forbidden_actions or []
    if objective_id == "OP09_FLEET_PRODUCTION_OPTIMIZATION":
        if "autonomous_fleet_frequency_override" not in forbidden:
            print(f"  {FAIL} OP09 missing critical safety gate: autonomous_fleet_frequency_override")
            return False
        print(f"  {PASS} Fleet frequency override forbidden (OP09 specific)")
    elif forbidden:
        print(f"  {INFO} Forbidden actions: {', '.join(forbidden)}")
    
    # Verify no single-asset tools in required_tools (fleet objectives shouldn't need asset_id)
    single_asset_tools = {"get_asset_context", "get_latest_telemetry", "calculate_operating_point"}
    found_single = single_asset_tools.intersection(set(obj_def.required_tools or []))
    if found_single:
        print(f"  {WARN} Fleet objective includes single-asset tools: {found_single} (verify this is intentional)")
    else:
        print(f"  {PASS} No single-asset tools in required_tools (fleet-scoped only)")
    
    return True


def test_evidence_requirements(registry: ObjectiveRegistry, objective_id: str,
                               verbose: bool = False) -> bool:
    """
    Phase 4: Verify required evidence types are appropriate for fleet scope.
    """
    hr(f"Phase 4 — Evidence Requirements: {objective_id}")
    
    obj_def = registry.get(objective_id)
    evidence = obj_def.required_evidence or []
    
    # All fleet objectives must require "fleet_asset_list"
    if "fleet_asset_list" not in evidence:
        print(f"  {FAIL} Missing required evidence: 'fleet_asset_list' (mandatory for fleet objectives)")
        return False
    print(f"  {PASS} Fleet asset list required")
    
    # Check for appropriate fleet-tier evidence types
    fleet_evidence = {
        "fleet_health_ranking", "fleet_summary_metrics", "fleet_headroom_ranking",
        "fleet_sizing_audit", "historical_case_matches"
    }
    found_fleet = fleet_evidence.intersection(set(evidence))
    
    if found_fleet:
        print(f"  {PASS} Fleet-tier evidence types: {', '.join(found_fleet)}")
    else:
        print(f"  {INFO} No fleet-specific evidence beyond asset list (may be acceptable)")
    
    # Single-asset evidence in fleet objective is suspicious
    single_evidence = {"current_snapshot", "6h_history", "24h_history"}
    found_single = single_evidence.intersection(set(evidence))
    if found_single:
        print(f"  {WARN} Single-asset evidence in fleet objective: {found_single} (verify design intent)")
    
    if verbose:
        print(f"\n  {INFO} All required evidence: {', '.join(evidence)}")
    
    return True


def run_full_verification(objective_id: Optional[str] = None, verbose: bool = False) -> Dict[str, bool]:
    """
    Run all 4 verification phases for specified objective(s).
    """
    print("=" * 80)
    print("  ESP Agent - Multi-Fleet Phases Verification")
    print("=" * 80)
    
    # Initialize registry and router
    registry = ObjectiveRegistry()
    router = IntentRouter(registry=registry)
    
    # Determine which objectives to test
    if objective_id:
        if objective_id not in FLEET_OBJECTIVES:
            print(f"\n{FAIL} Unknown objective: {objective_id}")
            print(f"Available: {', '.join(FLEET_OBJECTIVES.keys())}")
            sys.exit(1)
        test_objectives = {objective_id: FLEET_OBJECTIVES[objective_id]}
    else:
        test_objectives = FLEET_OBJECTIVES
    
    results = {}
    
    for obj_id, config in test_objectives.items():
        print(f"\n\n{'=' * 80}")
        print(f"Testing: {obj_id} - {config['title']}")
        print(f"{'=' * 80}")
        
        phase1 = test_objective_registration(registry, obj_id, config, verbose)
        phase2 = test_routing_confidence(router, obj_id, config, verbose)
        phase3 = test_safety_constraints(registry, obj_id, verbose)
        phase4 = test_evidence_requirements(registry, obj_id, verbose)
        
        all_passed = phase1 and phase2 and phase3 and phase4
        results[obj_id] = all_passed
        
        status = f"{PASS} ALL PHASES PASSED" if all_passed else f"{FAIL} SOME PHASES FAILED"
        print(f"\n{status} - {obj_id}")
    
    return results


def print_summary(results: Dict[str, bool]):
    """
    Print final verification summary with pass/fail counts.
    """
    hr("Final Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n{'Objective':<40} {'Status':<20}")
    print('-' * 60)
    
    for obj_id, passed_all in results.items():
        status = f"{PASS} PASSED" if passed_all else f"{FAIL} FAILED"
        print(f"{obj_id:<40} {status}")
    
    print('-' * 60)
    print(f"\nOverall: {passed}/{total} fleet objectives verified")
    
    if passed == total:
        print(f"\n{PASS} All fleet phases operational!")
        return 0
    else:
        print(f"\n{FAIL} Some fleet objectives require attention")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Verify ESP Agent multi-fleet objective phases (OP08-OP13)"
    )
    parser.add_argument(
        "--objective",
        choices=list(FLEET_OBJECTIVES.keys()),
        help="Test a single objective instead of all fleet objectives"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output for each test phase"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for CI/CD integration)"
    )
    
    args = parser.parse_args()
    
    try:
        results = run_full_verification(args.objective, args.verbose)
        
        if args.json:
            print("\n" + json.dumps(results, indent=2))
            sys.exit(0 if all(results.values()) else 1)
        
        exit_code = print_summary(results)
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"\n{FAIL} Verification script crashed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
