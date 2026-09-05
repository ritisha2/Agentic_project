# ESP APM: Reference Registries + 4-Visual Fault Explainability Suite
## Master Implementation Plan

---

## Part 1 — Current Situation

### What We Have

| Asset | Location | Status | Flaw / Gap |
|---|---|---|---|
| **Raw Telemetry (labelled)** | `cced_esp/data/labelled.db` | ✅ 3.11M rows, 73 wells, 13 faults labeled | Source of truth — **read-only, do not touch** |
| **Raw Telemetry (unlabelled)** | `cced_esp/data/unlabelled.db` | ✅ 2.68M rows, live-ish historical | No fault labels, no scenario — used only for normal baseline extension |
| **Normalized Telemetry** | `cced_esp/data/normalized.db` | ✅ `opg_normalized_telemetry` table, $[0,1]$ features | Written by `code/pipeline/build_normalized_db.py` |
| **Calibration Registry** | `code/models/well_calibration_registry.json` | ⚠️ Exists (9,518 lines, 73 wells) | **Built from unlabelled data only** — contaminated by fault windows. Baseline P10–P90 includes fault-degraded readings. Also: **single-regime (no frequency binning)** |
| **Fault Registry (YAML)** | `cced_esp/config/fault_registry.yaml` | ✅ 13 faults, Pydantic schema, ML/Rule flags | No **empirical deviation signatures** — only human-authored rule thresholds |
| **ML Diagnostic Engine** | `code/models/` (WellDiagnosticEngine) | ✅ Physics rules + Isolation Forest | Heuristic relative thresholds, not trained against labeled ground truth |
| **ESP ML Pipeline** | `cced_esp/ml/` (full pipeline) | ✅ fault_classifier, explainer, ground_truth_service | `explainer.py` has stub SHAP (deviation ÷ 100), not TreeSHAP |
| **EDA Dashboard** | `code/eda/dashboard.py` (6,384 lines) | ✅ 10 tabs, research-grade | Operator unusable (10 tabs, 30+ charts), missing Visual 2 (Depth/Pressure Profile) |
| **Agent Streamlit** | `agent_streamlit.py` | ✅ Chat interface | No inline Plotly rendering of the 4 forensic visuals |
| **MQTT Broker** | `cced_esp/backend/mqtt_collector.py` | ⏳ **Goes live Monday** | Live sensor stream → VFD diagnostic service → `vfd_diagnostics.jsonl` |

### The Core Gap

```
TODAY (OFFLINE)                              MONDAY (LIVE MQTT)
labelled.db                                  MQTT stream → opg_well_telemetry
     │                                               │
     ▼                                               ▼
❌ No regime-segmented normal baseline        ❌ No reference to score against
❌ No empirical fault deviation templates    ❌ No auto-caption ("closest match: gas lock")
❌ Calibration registry contaminated         ❌ 4 visuals don't exist yet
     │                                               │
     └───────────────── Gap ─────────────────────────┘
```

---

## Part 2 — Current Stage: The 4 Visuals (All Documented)

All 4 forensic visual specifications are now fully authored and grounded in real `cced_esp/data/labelled.db` ground-truth data:

1. **Visual 1** — [`visual1.md`](file:///x:/TAS/Agentic_project/visual1.md) ✅:
   - **Forensic Tipping Timeline:** 3-row synchronized time-series (Hydraulic / Electrical / Thermal+Mechanical) with P10–P90 baseline corridor and vertical red marker at the exact moment of trip. Ground-truth case: `FSWS-003`. Scaffold exists at `code/eda/figure_factory.py`.
2. **Visual 2** — [`visual2.md`](file:///x:/TAS/Agentic_project/visual2.md) ✅:
   - **Subsystem Health Equalizer & Well Pressure Profile:** Horizontal divergent bar equalizer (Motor, Hydraulics, Thermal, Mechanics) with automated cosine similarity auto-caption. Promotes to lead's **Vertical Wellbore Depth vs Pressure Profile** (`media_1788607948984.png`) when PIP, PDP, and WHP sensors are all present and the fault is Hydraulic ($\Delta P = 0\text{ psi}$).
3. **Visual 3** — [`visual3.md`](file:///x:/TAS/Agentic_project/visual3.md) ✅:
   - **In-Situ $H-Q$ Pump Performance Curve:** Affinity Law scaling ($60\text{ Hz} \rightarrow f\text{ Hz}$), Recommended Operating Range (ROR) thrust band, Best Efficiency Point (BEP), and actual operating point $(Q_{\text{actual}}, H_{\text{actual}})$. Proves hardware mechanical integrity vs. reservoir starvation.
4. **Visual 4** — [`visual4.md`](file:///x:/TAS/Agentic_project/visual4.md) ✅:
   - **SHAP Feature Attribution Waterfall & Operator Action Playbook:** Additive Shapley feature receipts ($\phi_i$), differential diagnosis ruling-out matrix, and 4-tier prescriptive field remediation SOP (Immediate, Surface, Verification, and Safety Interlocks).

---

## Part 3 — The Two Derived Reference Artifacts

### Why "Derived Artifacts" (Not a Forked Database)
`labelled.db` is the annotation layer. Raw sensor readings stay where they are. We extract two **static computed JSON files** from it, version them, and every consumer (dashboard, agent, visuals) reads from JSON — never from the live labeled DB at runtime.

```
cced_esp/data/labelled.db  (read ONCE, offline, today)
         │
         ├──► [Script] cced_esp/scripts/build_reference_artifacts.py
         │
         ├──── OUTPUT 1: cced_esp/data/artifacts/regime_baseline_registry.json
         │              (normal-only, frequency-binned P10/P90 per well per sensor)
         │
         └──── OUTPUT 2: cced_esp/data/artifacts/fault_signature_library.json
                        (empirical deviation vectors per fault type + 80/20 validation accuracy)
```

---

### Artifact 1: Regime-Segmented Baseline Registry

**Purpose:** Clean baseline built exclusively from rows labeled `normal` / `HEALTHY` in `labelled.db`, segmented by VFD frequency regime bins ($35\text{–}42\text{ Hz}$, $42\text{–}48\text{ Hz}$, $48\text{–}54\text{ Hz}$, $54\text{–}60\text{ Hz}$).

**Schema (`regime_baseline_registry.json`):**
```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-09-05T18:00:00Z",
  "source": "cced_esp/data/labelled.db (normal/HEALTHY rows only)",
  "wells": {
    "FSWS-003": {
      "regime_freq_35_42_hz": {
        "sample_count": 12450,
        "sensors": {
          "Inp bar/psi":        { "p10": 310.2, "median": 345.0, "p90": 380.1, "std": 22.4 },
          "Disch pr. Bar/psi":  { "p10": 1650.0, "median": 1820.0, "p90": 1940.0, "std": 95.0 },
          "VSD Amps/Load":      { "p10": 48.0, "median": 54.2, "p90": 61.0, "std": 4.1 },
          "Motor temp °C":      { "p10": 65.0, "median": 72.0, "p90": 78.5, "std": 3.8 },
          "Vibration G's-Vx":   { "p10": 0.04, "median": 0.09, "p90": 0.18, "std": 0.03 },
          "Leak Current Ct":    { "p10": 14.5, "median": 14.9, "p90": 15.3, "std": 0.2 },
          "Volt":               { "p10": 285.0, "median": 294.5, "p90": 305.0, "std": 6.5 }
        }
      },
      "regime_freq_42_48_hz": { "..." : "..." },
      "regime_freq_48_54_hz": { "..." : "..." },
      "regime_freq_54_60_hz": { "..." : "..." }
    }
  }
}
```

---

### Artifact 2: Fault Signature Library

**Purpose:** Canonical empirical deviation vectors across the 13 labeled fault modes. Used to power the SHAP waterfall, auto-captions, and agent hypothesis ranking.

**Schema (`fault_signature_library.json`):**
```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-09-05T18:00:00Z",
  "source": "cced_esp/data/labelled.db (fault-labeled rows)",
  "validation": {
    "train_split": 0.8,
    "test_split": 0.2,
    "top1_accuracy": 0.87,
    "f1_macro": 0.83
  },
  "faults": {
    "GAS_LOCK_UNDERLOAD": {
      "incident_count_total": 14,
      "incident_count_train": 11,
      "incident_count_test": 3,
      "primary_subsystem": "HYDRAULIC",
      "severity": "CRITICAL",
      "signature_vector": {
        "Inp bar/psi":        { "mean_deviation_pct": -42.5, "z_score": -2.8, "direction": "DOWN", "weight": 0.35 },
        "Disch pr. Bar/psi":  { "mean_deviation_pct": -58.0, "z_score": -3.4, "direction": "DOWN", "weight": 0.30 },
        "VSD Amps/Load":      { "mean_deviation_pct": -31.2, "z_score": -2.1, "direction": "DOWN", "weight": 0.20 },
        "Motor temp °C":      { "mean_deviation_pct": +14.8, "z_score": +1.5, "direction": "UP",   "weight": 0.10 },
        "Vibration G's-Vx":   { "mean_deviation_pct": +45.0, "z_score": +2.2, "direction": "UP",   "weight": 0.05 }
      },
      "exclusion_criteria": {
        "rules_out": ["SAND_INGESTION_JAM", "BEARING_DEGRADATION"],
        "reason": "Gas lock has low vibration and low current; sand/bearing faults show high vibration and high current"
      }
    }
  }
}
```

---

## Part 4 — Storage & Decoupled Architecture

### Single Source of Truth (`figure_factory.py`)

To prevent code duplication and avoid Streamlit import crashes in the agent, all rendering logic is housed in a decoupled figure factory returning pure Plotly `go.Figure` objects:

```
                  ┌───────────────────────────────────────────────┐
                  │   code/eda/figure_factory.py (Pure Plotly)   │
                  │   Returns go.Figure objects. ZERO Streamlit.  │
                  └───────────────────────┬───────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
       [ML Dashboard: Tab 11]                         [Agent Chat Interface]
   `code/eda/dashboard.py`                             `agent_streamlit.py`
   st.plotly_chart(fig1..4)                           st.plotly_chart(fig1..4)
```

**Location of Artifacts:** `cced_esp/data/artifacts/`
* `regime_baseline_registry.json`
* `fault_signature_library.json`
* `build_manifest.json`

---

## Part 5 — ML Dashboard Integration: Tab 11 Architecture

Instead of cluttering the existing 10 tabs, we introduce **Tab 11: "🎯 4-Visual Incident Forensics"** in `code/eda/dashboard.py`.

### Tab 11 Layout Specification:

```
====================================================================================================
 TAB 11: 🎯 4-VISUAL INCIDENT FORENSICS (EXECUTIVE DECISION SUITE)
====================================================================================================
 [Control Bar]
 Select Well ID: [ FSWS-003 ▼ ]  |  Select Incident: [ 2026-03-12 14:15:00 — Gas Lock Underload ▼ ]
 
 [Status Banner]
 🚨 Primary Fault: Gas Lock Underload | Confidence: 94.2% | Health Index: 28/100 | Severity: CRITICAL
----------------------------------------------------------------------------------------------------
 [2x2 Executive Visual Grid]
 
 ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────────┐
 │ CARD 1: VISUAL 1 (TIMELINE)             │  │ CARD 2: VISUAL 2 (PRESSURE PROFILE / EQ)│
 │ • Synchronized 3-Row Tipping Timeline   │  │ • Surface-to-Reservoir Depth Profile    │
 │ • Pre-fault window [-24h : +2h]         │  │ • Measured stage ΔP = 0 psi             │
 │ • P10-P90 baseline corridor shading     │  │ • (Or Subsystem Equalizer for Electrical)│
 │ • Red dashed trip marker                │  │ • Cosine similarity auto-caption        │
 └─────────────────────────────────────────┘  └─────────────────────────────────────────┘
 
 ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────────┐
 │ CARD 3: VISUAL 3 (PUMP H-Q CURVE)       │  │ CARD 4: VISUAL 4 (SHAP + PLAYBOOK)      │
 │ • Manufacturer H-Q at 44 Hz             │  │ • Additive SHAP waterfall receipts      │
 │ • Green ROR band & BEP marker           │  │ • Red driver bars vs Green dampener bars│
 │ • Operating point at 0 BPD (deadhead)   │  │ • 4-tier prescriptive operator playbook │
 │ • Proves hardware is intact (gas lock)  │  │ • Critical DO NOT RESTART safety warning│
 └─────────────────────────────────────────┘  └─────────────────────────────────────────┘
====================================================================================================
```

### Python Structure in `code/eda/dashboard.py`:

```python
# In dashboard.py around line 4719:
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "📈 Subsystem Subplots",
    "🎛️ Custom Multi-Sensor Overlay",
    "📊 Statistical EDA & Correlations",
    "🔍 Anomaly & 13-Fault Timeline",
    "📉 Trends & Degradation",
    "⚡ Events & Incidents Log",
    "🌐 Fleet Fault Finder (All Wells)",
    "🎯 Fault POC & Ground Truth Verification",
    "🔮 Prognostics, H-Q & Corridors",
    "📋 Data Table Explorer",
    "🎯 4-Visual Incident Forensics"  # <-- NEW TAB 11
])

with tab11:
    render_tab11_incident_forensics(
        selected_well_id=selected_well_id,
        df_filtered=df_filtered,
        registry=get_calibration_registry(),
        key_prefix="tab11_forensics"
    )
```

`render_tab11_incident_forensics` simply calls:
1. `fig1 = figure_factory.render_incident_tipping_timeline(...)`
2. `fig2 = figure_factory.render_subsystem_equalizer(...)` (or `render_pressure_depth_profile(...)`)
3. `fig3 = figure_factory.render_hq_performance_curve(...)`
4. `fig4 = figure_factory.render_shap_playbook_waterfall(...)`
5. Renders them in 2 columns using `st.plotly_chart`.

---

## Part 6 — Build Script Specification: `build_reference_artifacts.py`

**Path:** `cced_esp/scripts/build_reference_artifacts.py`  
**Execution:** Offline, run once against `cced_esp/data/labelled.db`.

```python
"""
Extracts regime-segmented baselines and empirical fault deviation templates from labelled.db.
Outputs:
1. cced_esp/data/artifacts/regime_baseline_registry.json
2. cced_esp/data/artifacts/fault_signature_library.json
3. cced_esp/data/artifacts/build_manifest.json
"""
```

**Steps:**
1. Connect to `cced_esp/data/labelled.db`.
2. Extract all rows where fault label is `normal` or `HEALTHY`.
3. Bin rows into 4 frequency buckets: $[35, 42), [42, 48), [48, 54), [54, 60]\text{ Hz}$.
4. Compute $P_{10}, P_{90}$, median, mean, std per well per sensor per bucket $\rightarrow$ Write `regime_baseline_registry.json`.
5. Group fault incidents $\rightarrow$ 80% train / 20% test holdout split.
6. Compute mean z-score deviation vector per fault mode on train split.
7. Run Cosine Similarity evaluation on 20% holdout split; verify Top-1 accuracy $\ge 0.75$.
8. Write `fault_signature_library.json` and `build_manifest.json`.

---

## Part 7 — Sequenced Implementation Roadmap

```
STAGE 0  (Offline Calibration)
├── Create cced_esp/scripts/build_reference_artifacts.py
├── Run build script against labelled.db
├── Verify regime_baseline_registry.json and fault_signature_library.json
└── Validate Top-1 classification accuracy on 20% holdout

STAGE 1  (Figure Factory Implementation in code/eda/figure_factory.py)
├── Visual 1: render_incident_tipping_timeline() (wire to regime baseline)
├── Visual 2: render_subsystem_equalizer() & render_pressure_depth_profile()
├── Visual 3: render_hq_performance_curve() (with Affinity Law scaling)
└── Visual 4: render_shap_playbook_waterfall() (with SOP card generation)

STAGE 2  (ML Dashboard Integration)
├── Add Tab 11 ("🎯 4-Visual Incident Forensics") to code/eda/dashboard.py
├── Implement 2x2 executive card layout calling figure_factory.py
└── Test interactive incident selection on Well FSWS-003

STAGE 3  (Agent Streamlit Integration)
├── Connect agent_streamlit.py to figure_factory.py
└── Test inline Plotly figure rendering when operator queries an incident in chat
```
