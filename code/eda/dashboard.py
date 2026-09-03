"""
CCED VFD Interactive Time-Series EDA & Diagnostic Dashboard
===========================================================
Streamlit + Plotly interactive dashboard for exploring timestamp-wise
sensor telemetry, physics dynamics, correlations, trend degradation, operational events,
and cross-well fleet fault history across 73 CCED wells.
"""

import os
import sys
import glob
import re
import datetime
import sqlite3
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Configure page layout
st.set_page_config(
    page_title="CCED VFD Well EDA & Diagnostic Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure parent directory (containing models package) and current directory are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
root_dir = os.path.abspath(os.path.join(parent_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from models import WellDiagnosticEngine, STANDARD_SENSORS, clean_col_key, FAULT_DEFINITIONS
    HAS_MODELS = True
except Exception as e:
    HAS_MODELS = False
    print(f"Warning: Could not import models package: {e}")

try:
    from figure_factory import render_incident_tipping_timeline, build_evidence_comparison_table
except ImportError:
    try:
        from eda.figure_factory import render_incident_tipping_timeline, build_evidence_comparison_table
    except ImportError:
        render_incident_tipping_timeline = None
        build_evidence_comparison_table = None

CATEGORIZED_DIR = r"C:\Users\admin.DESKTOP-17T37DJ\Desktop\cced\categorized_wells"
UNLABELLED_DB_PATH = os.path.abspath(os.path.join(root_dir, "cced_esp", "data", "unlabelled.db"))
if not os.path.exists(UNLABELLED_DB_PATH):
    UNLABELLED_DB_PATH = os.path.abspath(os.path.join(parent_dir, "..", "cced_esp", "data", "unlabelled.db"))
NORMALIZED_DB_PATH = os.path.abspath(os.path.join(root_dir, "cced_esp", "data", "normalized.db"))
if not os.path.exists(NORMALIZED_DB_PATH):
    NORMALIZED_DB_PATH = os.path.abspath(os.path.join(parent_dir, "..", "cced_esp", "data", "normalized.db"))


@st.cache_resource
def get_diagnostic_engine():
    """Initializes and caches the WellDiagnosticEngine."""
    if HAS_MODELS:
        cat_dir = CATEGORIZED_DIR if os.path.exists(CATEGORIZED_DIR) else None
        return WellDiagnosticEngine(categorized_dir=cat_dir)
    return None


@st.cache_data(show_spinner=False)
def discover_all_wells(base_dir: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Scans categorized directory or unlabelled.db and returns all available wells organized by family cluster.
    """
    wells_by_cluster = {}
    if os.path.exists(base_dir):
        csv_files = glob.glob(os.path.join(base_dir, "**", "*.csv"), recursive=True)
        for f in csv_files:
            if "Wells_Summary_Index" in f:
                continue
            fname = os.path.splitext(os.path.basename(f))[0]
            well_id = fname.replace("_", "-")
            
            # Determine cluster folder
            parent_folder = os.path.basename(os.path.dirname(f))
            m = re.match(r'^([A-Za-z]+)', well_id)
            cluster = parent_folder if parent_folder and parent_folder.upper() in ["FS", "FNW", "FWS", "ULFA"] else (m.group(1).upper() if m else "OTHER")
            
            if cluster not in wells_by_cluster:
                wells_by_cluster[cluster] = []
            
            wells_by_cluster[cluster].append({
                "well_id": well_id,
                "path": f,
                "filename": os.path.basename(f)
            })

    # Fallback to local unlabelled.db if base_dir is missing or empty
    if not wells_by_cluster and os.path.exists(UNLABELLED_DB_PATH):
        try:
            conn = sqlite3.connect(UNLABELLED_DB_PATH)
            df_w = pd.read_sql_query("SELECT DISTINCT well_id FROM opg_well_telemetry ORDER BY well_id", conn)
            conn.close()
            for well_id in df_w["well_id"].dropna().tolist():
                m = re.match(r'^([A-Za-z]+)', well_id)
                cluster = m.group(1).upper() if m else "OTHER"
                if cluster not in wells_by_cluster:
                    wells_by_cluster[cluster] = []
                wells_by_cluster[cluster].append({
                    "well_id": well_id,
                    "path": f"sqlite://{well_id}",
                    "filename": f"{well_id}.db"
                })
        except Exception as e:
            print(f"Warning querying unlabelled.db for wells: {e}")
        
    for k in wells_by_cluster:
        wells_by_cluster[k].sort(key=lambda x: x["well_id"])
        
    return wells_by_cluster


@st.cache_data(show_spinner=False)
def load_incident_telemetry_window(well_id: str, center_ts: str, window_minutes: int = 60) -> pd.DataFrame:
    """Loads a high-resolution window around an incident timestamp for forensic inspection."""
    if not os.path.exists(NORMALIZED_DB_PATH):
        return pd.DataFrame()
    try:
        clean_ts = str(center_ts).replace("Z", "+00:00")
        dt_center = pd.to_datetime(clean_ts, utc=True)
        half_win = pd.Timedelta(minutes=window_minutes / 2)
        start_iso = (dt_center - half_win).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = (dt_center + half_win).strftime("%Y-%m-%dT%H:%M:%SZ")

        with sqlite3.connect(NORMALIZED_DB_PATH) as conn:
            q = """
                SELECT timestamp AS Report_DateTime, *
                FROM opg_normalized_telemetry
                WHERE Wells = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                LIMIT 500
            """
            df = pd.read_sql_query(q, conn, params=(well_id, start_iso, end_iso))
            if not df.empty:
                return df.loc[:, ~df.columns.duplicated()].copy()

            # Fallback: if bounds were too tight, fetch closest 60 rows
            q_fallback = """
                SELECT timestamp AS Report_DateTime, *
                FROM opg_normalized_telemetry
                WHERE Wells = ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 60
            """
            df_fallback = pd.read_sql_query(q_fallback, conn, params=(well_id, str(center_ts)))
            if not df_fallback.empty:
                return df_fallback.sort_values("Report_DateTime").loc[:, ~df_fallback.columns.duplicated()].copy()
    except Exception as e:
        print(f"Error loading incident telemetry window: {e}")
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_well_dataset(file_path: str) -> pd.DataFrame:
    """Loads a well dataset from disk or unlabelled.db, parses datetime, and cleans columns."""
    df = pd.DataFrame()

    if file_path.startswith("sqlite://") or (not os.path.exists(file_path) and (os.path.exists(NORMALIZED_DB_PATH) or os.path.exists(UNLABELLED_DB_PATH))):
        well_id = file_path.replace("sqlite://", "") if file_path.startswith("sqlite://") else os.path.splitext(os.path.basename(file_path))[0].replace("_", "-")
        # 1. Try pre-computed normalized.db feature store
        if os.path.exists(NORMALIZED_DB_PATH):
            try:
                conn_norm = sqlite3.connect(NORMALIZED_DB_PATH)
                q_norm = """
                    SELECT timestamp AS Report_DateTime, *
                    FROM opg_normalized_telemetry
                    WHERE Wells = ?
                    ORDER BY id DESC
                    LIMIT 10000
                """
                df = pd.read_sql_query(q_norm, conn_norm, params=(well_id,))
                conn_norm.close()
                if not df.empty:
                    df = df.loc[:, ~df.columns.duplicated()].copy()
            except Exception as e:
                df = pd.DataFrame()

        # 2. Fallback to unlabelled.db if normalized.db not built or empty for this well
        if df.empty and os.path.exists(UNLABELLED_DB_PATH):
            try:
                conn = sqlite3.connect(UNLABELLED_DB_PATH)
                query = """
                    SELECT timestamp AS Report_DateTime,
                           COALESCE(intake_pressure_psi, 237.0) AS [Inp bar/psi],
                           COALESCE(discharge_pressure_psi, pressure_psi, 1895.0) AS [Disch pr. Bar/psi],
                           COALESCE(motor_temperature_c, temperature_c, 78.9) AS [Motor temp °C],
                           COALESCE(intake_temperature_c, 52.0) AS [Int temp °C],
                           COALESCE(motor_current_a, 18.9) AS [VSD Amps/Load],
                           COALESCE(motor_voltage_v, 1009.0) AS [Volt],
                           COALESCE(frequency_hz, 46.2) AS Frequency,
                           COALESCE(vibration_g, 0.18) AS [Vibration G's-Vx],
                           COALESCE(vfd_status, 1) AS [VFD STS],
                           COALESCE(leak_current_ct, 0.0) AS [Leak Current Ct],
                           COALESCE(dhg_current, 0.0) AS [DHG Current],
                           COALESCE(whp_psi, 255.0) AS [WHP (PSI)],
                           COALESCE(flp_psi, 249.0) AS [FLP (PSI)],
                           COALESCE(annulus_pressure_psi, 0.0) AS [AP (PSI)],
                           COALESCE(flow_rate_bpd, 745.0) AS Flow_BPD
                    FROM opg_well_telemetry
                    WHERE well_id = ?
                    ORDER BY id DESC
                    LIMIT 10000
                """
                df = pd.read_sql_query(query, conn, params=(well_id,))
                conn.close()
            except Exception as e:
                print(f"Error loading well {well_id} from unlabelled.db: {e}")
                return pd.DataFrame()
    elif os.path.exists(file_path):
        df = pd.read_csv(file_path, low_memory=False)
        # Standardize column names
        col_map = {}
        for c in df.columns:
            if c.startswith("norm_"):
                col_map[c] = c
            else:
                col_map[c] = clean_col_key(c)
        df.rename(columns=col_map, inplace=True)
        df = df.loc[:, ~df.columns.duplicated()].copy()
    else:
        return pd.DataFrame()

    if df.empty:
        return df

    # Parse timestamp
    if "Report_DateTime" in df.columns:
        df["Report_DateTime"] = pd.to_datetime(df["Report_DateTime"], errors="coerce")
        df.sort_values("Report_DateTime", inplace=True)
        df.dropna(subset=["Report_DateTime"], inplace=True)
        df.reset_index(drop=True, inplace=True)
    elif "File_DateTime" in df.columns:
        df["Report_DateTime"] = pd.to_datetime(df["File_DateTime"], errors="coerce")
        df.sort_values("Report_DateTime", inplace=True)
        df.dropna(subset=["Report_DateTime"], inplace=True)
        df.reset_index(drop=True, inplace=True)

    # Convert all sensor and normalized columns to numeric float
    all_numeric_targets = [
        "Inp bar/psi", "Disch pr. Bar/psi", "VSD Amps/Load", "Frequency", "Volt",
        "Motor temp °C", "Int temp °C", "Vibration G's-Vx", "Leak Current Ct",
        "DHG Current", "WHP (PSI)", "FLP (PSI)", "AP (PSI)", "VFD STS"
    ] + [c for c in df.columns if c.startswith("norm_")]

    for col in all_numeric_targets:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            # Clear legacy 1.0 unmonitored flatlines on surface sensors to 0.0
            if col in ["WHP (PSI)", "FLP (PSI)", "AP (PSI)"] and df[col].nunique() <= 1 and df[col].iloc[0] in [1.0, 0.0, 1, 0]:
                df[col] = 0.0

    # Compute derived physics features
    if "Inp bar/psi" in df.columns and "Disch pr. Bar/psi" in df.columns:
        df["ΔP Head (PSI)"] = df["Disch pr. Bar/psi"] - df["Inp bar/psi"]
    if "VSD Amps/Load" in df.columns and "Frequency" in df.columns:
        df["Torque Proxy (A/Hz)"] = df["VSD Amps/Load"] / df["Frequency"].replace(0, 1.0)
    if "Volt" in df.columns and "VSD Amps/Load" in df.columns:
        df["Power Proxy (kVA)"] = (df["Volt"] * df["VSD Amps/Load"] * 1.732) / 1000.0
    if "Motor temp °C" in df.columns and "Int temp °C" in df.columns:
        df["Thermal Elevation (°C)"] = df["Motor temp °C"] - df["Int temp °C"]
        
    # Dynamically generate norm_* features if missing
    if not any(c.startswith("norm_") for c in df.columns):
        engine = get_diagnostic_engine()
        if engine:
            well_target = file_path.replace("sqlite://", "") if file_path.startswith("sqlite://") else "FS-031"
            norm_records = []
            for _, r in df.iterrows():
                try:
                    n_res = engine.normalizer.normalize_live_telemetry(well_target, r.to_dict())
                    norm_dict = {f"norm_{clean_col_key(k)}": float(v) for k, v in n_res.get("normalized", {}).items()}
                    norm_records.append(norm_dict)
                except Exception:
                    norm_records.append({})
            if norm_records:
                df_norm = pd.DataFrame(norm_records)
                for col in df_norm.columns:
                    df[col] = df_norm[col].values

    return df


def resample_dataframe(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Downsamples dataframe for smooth and responsive plotting."""
    if rule == "Raw (All Points)" or len(df) <= 500:
        return df
    
    rule_map = {
        "15 Minutes": "15min",
        "1 Hour": "1h",
        "4 Hours": "4h",
        "1 Day": "1D"
    }
    freq = rule_map.get(rule, "1h")
    
    df_indexed = df.set_index("Report_DateTime")
    numeric_cols = df_indexed.select_dtypes(include=[np.number]).columns
    df_resampled = df_indexed[numeric_cols].resample(freq).mean().dropna(how="all").reset_index()
    return df_resampled


def compute_trends_and_slopes(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes linear trend slopes over the selected time-series for key degradation indicators.
    """
    if len(df) < 5 or "Report_DateTime" not in df.columns:
        return {}
    
    # Days delta array
    t0 = df["Report_DateTime"].min()
    days = (df["Report_DateTime"] - t0).dt.total_seconds() / 86400.0
    total_days = max(1.0, float(days.max()))

    trends = {}
    targets = [
        ("ΔP Head (PSI)", "Head Degradation Slope", "PSI / Day", -5.0),
        ("Motor temp °C", "Motor Thermal Slope", "°C / Day", 0.5),
        ("VSD Amps/Load", "Electrical Amperage Drift", "A / Day", 1.0),
        ("Inp bar/psi", "Intake Pressure Depletion", "PSI / Day", -3.0),
        ("Vibration G's-Vx", "Vibration Growth Rate", "G / Day", 0.01)
    ]

    for col, title, unit, critical_threshold in targets:
        if col in df.columns:
            s_vals = df[col].values
            # Filter non-zero operating values
            valid_mask = ~np.isnan(s_vals) & (s_vals != 0)
            if np.sum(valid_mask) > 5:
                x_sub = days.values[valid_mask]
                y_sub = s_vals[valid_mask]
                # Linear fit y = mx + c
                poly = np.polyfit(x_sub, y_sub, 1)
                slope = float(poly[0])
                start_val = float(poly[1])
                end_val = float(slope * total_days + start_val)

                # Status determination
                if col in ["ΔP Head (PSI)", "Inp bar/psi"]:
                    status = "🔴 DEGRADING RAPIDLY" if slope < critical_threshold else ("🟡 SLIGHT DECLINE" if slope < 0 else "🟢 STABLE / IMPROVING")
                elif col in ["Motor temp °C", "VSD Amps/Load", "Vibration G's-Vx"]:
                    status = "🔴 RAPID HEATING / WEAR" if slope > critical_threshold else ("🟡 SLIGHT CREEP" if slope > 0.1 * critical_threshold else "🟢 STABLE")
                else:
                    status = "🟢 STABLE"

                trends[col] = {
                    "title": title,
                    "slope": round(slope, 3),
                    "unit": unit,
                    "status": status,
                    "start_val": round(start_val, 1),
                    "end_val": round(end_val, 1),
                    "total_change": round(end_val - start_val, 1)
                }

    return trends


def detect_operational_events(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Identifies discrete operational events (Trips, Startups, Vibration Surges, Pressure Collapses).
    """
    events = []
    if len(df) < 2 or "Report_DateTime" not in df.columns:
        return events

    # 1. Detect VFD Trips and Startups
    if "VFD STS" in df.columns:
        vfd = pd.to_numeric(df["VFD STS"], errors="coerce").fillna(0.0).values
        d_vfd = np.diff(vfd)
        
        for i, val in enumerate(d_vfd):
            dt_ts = df["Report_DateTime"].iloc[i+1]
            if val < 0:
                events.append({
                    "timestamp": dt_ts,
                    "event_type": "🔴 VFD Trip / Shutdown Event",
                    "severity": "HIGH",
                    "details": "VFD running status switched from 1 (Running) to 0 (Stopped).",
                    "amps": df["VSD Amps/Load"].iloc[i] if "VSD Amps/Load" in df else 0.0,
                    "m_temp": df["Motor temp °C"].iloc[i] if "Motor temp °C" in df else 0.0,
                    "vib": df["Vibration G's-Vx"].iloc[i] if "Vibration G's-Vx" in df else 0.0
                })
            elif val > 0:
                events.append({
                    "timestamp": dt_ts,
                    "event_type": "🟢 VFD Startup / Soft-Ramp Event",
                    "severity": "INFO",
                    "details": "VFD restarted and accelerated.",
                    "amps": df["VSD Amps/Load"].iloc[i+1] if "VSD Amps/Load" in df else 0.0,
                    "m_temp": df["Motor temp °C"].iloc[i+1] if "Motor temp °C" in df else 0.0,
                    "vib": df["Vibration G's-Vx"].iloc[i+1] if "Vibration G's-Vx" in df else 0.0
                })

    # 2. Detect Vibration Surges (> 0.30 G)
    if "Vibration G's-Vx" in df.columns:
        vib_series = df["Vibration G's-Vx"].values
        for i in range(1, len(vib_series)):
            if vib_series[i] >= 0.32 and vib_series[i-1] < 0.28:
                events.append({
                    "timestamp": df["Report_DateTime"].iloc[i],
                    "event_type": "⚠️ Vibration Surge Spike",
                    "severity": "WARNING",
                    "details": f"Radial vibration spiked to {vib_series[i]:.2f} G (Threshold: 0.30 G).",
                    "amps": df["VSD Amps/Load"].iloc[i] if "VSD Amps/Load" in df else 0.0,
                    "m_temp": df["Motor temp °C"].iloc[i] if "Motor temp °C" in df else 0.0,
                    "vib": vib_series[i]
                })

    # 3. Detect Severe Suction Depletion
    if "Inp bar/psi" in df.columns:
        inp_series = df["Inp bar/psi"].values
        med_inp = np.median(inp_series[inp_series > 0]) if np.any(inp_series > 0) else 400.0
        for i in range(1, len(inp_series)):
            if inp_series[i] < 0.20 * med_inp and inp_series[i-1] >= 0.20 * med_inp and inp_series[i] > 0:
                events.append({
                    "timestamp": df["Report_DateTime"].iloc[i],
                    "event_type": "⚠️ Intake Suction Depletion Event",
                    "severity": "WARNING",
                    "details": f"Intake collapsed to {inp_series[i]:.1f} PSI (Normal: {med_inp:.1f} PSI).",
                    "amps": df["VSD Amps/Load"].iloc[i] if "VSD Amps/Load" in df else 0.0,
                    "m_temp": df["Motor temp °C"].iloc[i] if "Motor temp °C" in df else 0.0,
                    "vib": df["Vibration G's-Vx"].iloc[i] if "Vibration G's-Vx" in df else 0.0
                })

    events.sort(key=lambda x: x["timestamp"])
    return events


@st.cache_data(show_spinner=False)
def scan_fleet_for_fault_history(target_fault: str, max_wells: int = 73) -> pd.DataFrame:
    """
    Scans historical data across all 73 categorized wells to find occurrences of the chosen fault type.
    """
    if not HAS_MODELS:
        return pd.DataFrame()

    engine = get_diagnostic_engine()
    if not engine:
        return pd.DataFrame()
    wells_dict = discover_all_wells(CATEGORIZED_DIR)
    
    all_wells = []
    for c, wlist in wells_dict.items():
        for w in wlist:
            all_wells.append((c, w["well_id"], w["path"]))

    fleet_matches = []

    for cluster, well_id, fpath in all_wells[:max_wells]:
        try:
            df = load_well_dataset(fpath)
            if df.empty:
                continue

            # Sample every Nth row to keep search fast across 3.35M rows
            sample_step = max(1, len(df) // 40)
            df_sampled = df.iloc[::sample_step]

            for _, row in df_sampled.iterrows():
                r_dict = row.to_dict()
                res = engine.evaluate_live_telemetry(well_id, r_dict, verbose=False)
                diag = res["diagnostic"]
                
                if diag["primary_fault"] == target_fault or target_fault in diag.get("all_scores", {}):
                    conf = diag.get("all_scores", {}).get(target_fault, diag["confidence"])
                    fleet_matches.append({
                        "Well_ID": well_id,
                        "Cluster": cluster,
                        "Timestamp": str(r_dict.get("Report_DateTime", "")),
                        "Detected_Fault": target_fault,
                        "Confidence": conf,
                        "Health_Score": diag["health_score"],
                        "Status": diag["status"],
                        "Intake_PSI": round(float(r_dict.get("Inp bar/psi", 0.0)), 1),
                        "Discharge_PSI": round(float(r_dict.get("Disch pr. Bar/psi", 0.0)), 1),
                        "Amps": round(float(r_dict.get("VSD Amps/Load", 0.0)), 1),
                        "Motor_Temp_C": round(float(r_dict.get("Motor temp °C", 0.0)), 1),
                        "Vibration_G": round(float(r_dict.get("Vibration G's-Vx", 0.0)), 2),
                        "Advisory": diag["action_advisory"]
                    })
        except Exception:
            continue

    return pd.DataFrame(fleet_matches)


def main():
    # -------------------------------------------------------------
    # Sidebar: Well Discovery & Controls
    # -------------------------------------------------------------
    st.sidebar.title("⚡ CCED VFD Analytics")
    st.sidebar.markdown("**ESP Telemetry, Trends, Events & Diagnostic Explorer**")
    st.sidebar.divider()
    
    # 1. Discover all wells
    wells_dict = discover_all_wells(CATEGORIZED_DIR)
    if not wells_dict:
        st.error(f"No categorized wells found in `{CATEGORIZED_DIR}`. Please run categorization first.")
        return

    clusters = list(wells_dict.keys())
    selected_cluster = st.sidebar.selectbox("📂 Select Field Cluster", clusters, index=0)
    
    cluster_wells = wells_dict[selected_cluster]
    well_names = [w["well_id"] for w in cluster_wells]
    selected_well_id = st.sidebar.selectbox("🛢️ Select Well ID", well_names, index=0)
    
    # Find selected well file
    well_info = next((w for w in cluster_wells if w["well_id"] == selected_well_id), cluster_wells[0])
    file_path = well_info["path"]
    
    # 2. Load Dataset
    with st.spinner(f"Loading data for {selected_well_id}..."):
        df = load_well_dataset(file_path)
        
    if df.empty:
        st.error(f"Could not load data for {selected_well_id} from `{file_path}`")
        return

    min_date = df["Report_DateTime"].min().date()
    max_date = df["Report_DateTime"].max().date()

    st.sidebar.divider()
    st.sidebar.subheader("📅 Date Range Filter")
    
    date_preset = st.sidebar.radio(
        "Range Presets",
        ["Full History", "Last 30 Days", "Last 7 Days", "Custom Range"],
        index=0
    )
    
    if date_preset == "Full History":
        start_date, end_date = min_date, max_date
    elif date_preset == "Last 30 Days":
        end_date = max_date
        start_date = max(min_date, max_date - datetime.timedelta(days=30))
    elif date_preset == "Last 7 Days":
        end_date = max_date
        start_date = max(min_date, max_date - datetime.timedelta(days=7))
    else:
        date_range = st.sidebar.date_input("Custom Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date

    # Filter dataframe by date
    mask = (df["Report_DateTime"].dt.date >= start_date) & (df["Report_DateTime"].dt.date <= end_date)
    df_filtered = df.loc[mask].copy()

    # 3. Data Resolution / Downsampling Toggle
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ Plotting Performance")
    total_pts = len(df_filtered)
    default_res = "1 Hour" if total_pts > 10000 else "Raw (All Points)"
    resample_rule = st.sidebar.selectbox(
        "Time Resolution",
        ["Raw (All Points)", "15 Minutes", "1 Hour", "4 Hours", "1 Day"],
        index=["Raw (All Points)", "15 Minutes", "1 Hour", "4 Hours", "1 Day"].index(default_res)
    )
    
    df_plot = resample_dataframe(df_filtered, resample_rule)

    # 4. View Mode Toggle
    st.sidebar.divider()
    st.sidebar.subheader("📊 Metric Mode")
    metric_view = st.sidebar.radio(
        "Sensor Units",
        ["Raw Engineering Units", "Normalized [0, 1] Features", "Derived Physics Dynamics"],
        index=0
    )

    # -------------------------------------------------------------
    # Main Dashboard Header & KPI Cards
    # -------------------------------------------------------------
    st.title(f"🛢️ Well Telemetry Dashboard: `{selected_well_id}`")
    st.caption(f"Field Cluster: **{selected_cluster}** | File: `{well_info['filename']}` | Records: **{len(df_filtered):,}** points from {start_date} to {end_date}")

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    inp_med = df_filtered["Inp bar/psi"].median() if "Inp bar/psi" in df_filtered else 0.0
    disch_med = df_filtered["Disch pr. Bar/psi"].median() if "Disch pr. Bar/psi" in df_filtered else 0.0
    amps_med = df_filtered["VSD Amps/Load"].median() if "VSD Amps/Load" in df_filtered else 0.0
    mtemp_med = df_filtered["Motor temp °C"].median() if "Motor temp °C" in df_filtered and len(df_filtered) > 0 else 0.0
    vib_max = float(df_filtered["Vibration G's-Vx"].max()) if "Vibration G's-Vx" in df_filtered and len(df_filtered) > 0 else 0.0
    if "VFD STS" in df_filtered.columns:
        vfd_series = pd.to_numeric(df_filtered["VFD STS"], errors="coerce").fillna(0.0)
        uptime_pct = float((vfd_series > 0).mean() * 100.0) if len(vfd_series) > 0 else 100.0
    else:
        uptime_pct = 100.0

    kpi1.metric("Intake Pressure", f"{inp_med:.1f} PSI", help="Median intake pressure")
    kpi2.metric("Discharge Pressure", f"{disch_med:.1f} PSI", help="Median discharge pressure")
    kpi3.metric("Motor Current", f"{amps_med:.1f} A", help="Median operating amperage")
    kpi4.metric("Motor Temp", f"{mtemp_med:.1f} °C", help="Median motor internal temperature")
    kpi5.metric("Peak Vibration", f"{vib_max:.2f} G", help="Maximum radial vibration observed")
    kpi6.metric("Active Uptime", f"{uptime_pct:.1f}%", help="Percentage of time VFD status = running")

    st.divider()

    # -------------------------------------------------------------
    # Tab Navigation
    # -------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📈 Subsystem Subplots",
        "🎛️ Custom Multi-Sensor Overlay",
        "📊 Statistical EDA & Correlations",
        "🔍 Anomaly & 13-Fault Timeline",
        "📉 Trends & Degradation",
        "⚡ Events & Incidents Log",
        "🌐 Fleet Fault Finder (All Wells)",
        "📋 Data Table Explorer"
    ])

    # =============================================================
    # TAB 1: Grouped Subsystem Subplots (Synchronized Timelines)
    # =============================================================
    with tab1:
        st.subheader("Subsystem Time-Series Analysis")
        st.caption("Synchronized physics subplots comparing hydraulic, electrical, thermal, and mechanical sensor trends.")

        tab1_view = st.radio(
            "📐 Subsystem Plot View Mode",
            [
                "⚡ Dual Synchronized View (Raw + Normalized Side-by-Side)",
                "📈 Raw Engineering Units (PSI, °C, A, V, Hz, G)",
                "📊 Normalized [0.0 - 1.0] Feature Space",
                "🔬 Derived Physics Dynamics (ΔP, Torque A/Hz, Power kVA, ΔT)"
            ],
            horizontal=True,
            index=0
        )

        if "Dual Synchronized" in tab1_view:
            fig_dual = make_subplots(
                rows=4, cols=2,
                shared_xaxes=True,
                vertical_spacing=0.06,
                horizontal_spacing=0.06,
                subplot_titles=(
                    "1. Raw Hydraulics (PSI)", "1. Normalized Hydraulics [0, 1]",
                    "2. Raw Electrical (V, A, Hz)", "2. Normalized Electrical [0, 1]",
                    "3. Raw Thermal (°C)", "3. Normalized Thermal [0, 1]",
                    "4. Raw Vibration (G) & VFD", "4. Normalized Vibration & Status [0, 1]"
                )
            )

            # --- Row 1: Hydraulics (Col 1: Raw, Col 2: Norm) ---
            if "Inp bar/psi" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Inp bar/psi"], name="Raw Intake (PSI)", line=dict(color="#00bcd4", width=1.5)), row=1, col=1)
            if "Disch pr. Bar/psi" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Disch pr. Bar/psi"], name="Raw Discharge (PSI)", line=dict(color="#2196f3", width=1.5)), row=1, col=1)
            if "ΔP Head (PSI)" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["ΔP Head (PSI)"], name="Raw ΔP Head (PSI)", line=dict(color="#9c27b0", width=1.2, dash="dot")), row=1, col=1)
            if "WHP (PSI)" in df_plot and df_plot["WHP (PSI)"].max() > 0:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["WHP (PSI)"], name="Raw WHP (PSI)", line=dict(color="#4caf50", width=1.2)), row=1, col=1)

            if "norm_Inp_bar_psi" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Inp_bar_psi"], name="norm_Inp [0, 1]", line=dict(color="#00bcd4", width=1.5)), row=1, col=2)
            if "norm_Disch_pr_Bar_psi" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Disch_pr_Bar_psi"], name="norm_Disch [0, 1]", line=dict(color="#2196f3", width=1.5)), row=1, col=2)
            if "norm_Delta_P_PSI" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Delta_P_PSI"], name="norm_ΔP [0, 1]", line=dict(color="#9c27b0", width=1.2, dash="dot")), row=1, col=2)
            if "norm_WHP_PSI" in df_plot and df_plot["norm_WHP_PSI"].max() > 0:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_WHP_PSI"], name="norm_WHP [0, 1]", line=dict(color="#4caf50", width=1.2)), row=1, col=2)

            # --- Row 2: Electrical ---
            if "VSD Amps/Load" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["VSD Amps/Load"], name="Raw Amps (A)", line=dict(color="#e91e63", width=1.5)), row=2, col=1)
            if "Volt" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Volt"], name="Raw Volts (V)", line=dict(color="#ffc107", width=1.2)), row=2, col=1)
            if "Frequency" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Frequency"], name="Raw Hz (Hz)", line=dict(color="#3f51b5", width=1.2, dash="dash")), row=2, col=1)

            if "norm_VSD_Amps_Load" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_VSD_Amps_Load"], name="norm_Amps [0, 1]", line=dict(color="#e91e63", width=1.5)), row=2, col=2)
            if "norm_Volt" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Volt"], name="norm_Volt [0, 1]", line=dict(color="#ffc107", width=1.2)), row=2, col=2)
            if "norm_Frequency" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Frequency"], name="norm_Freq [0, 1]", line=dict(color="#3f51b5", width=1.2, dash="dash")), row=2, col=2)

            # --- Row 3: Thermal ---
            if "Motor temp °C" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Motor temp °C"], name="Raw Motor Temp (°C)", line=dict(color="#f44336", width=1.5)), row=3, col=1)
            if "Int temp °C" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Int temp °C"], name="Raw Intake Temp (°C)", line=dict(color="#03a9f4", width=1.5)), row=3, col=1)

            if "norm_Motor_temp_C" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Motor_temp_C"], name="norm_Motor_Temp [0, 1]", line=dict(color="#f44336", width=1.5)), row=3, col=2)
            if "norm_Int_temp_C" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Int_temp_C"], name="norm_Intake_Temp [0, 1]", line=dict(color="#03a9f4", width=1.5)), row=3, col=2)

            # --- Row 4: Vibration & VFD Status ---
            if "Vibration G's-Vx" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Vibration G's-Vx"], name="Raw Vibration (G)", line=dict(color="#e91e63", width=1.5)), row=4, col=1)
            if "VFD STS" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["VFD STS"], name="Raw VFD Status", line=dict(color="#8bc34a", width=1.0)), row=4, col=1)

            if "norm_Vibration_G_s_Vx" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["norm_Vibration_G_s_Vx"], name="norm_Vibration [0, 1]", line=dict(color="#e91e63", width=1.5)), row=4, col=2)
            if "VFD STS" in df_plot:
                fig_dual.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["VFD STS"], name="norm_VFD_Status [0, 1]", line=dict(color="#8bc34a", width=1.0)), row=4, col=2)

            fig_dual.update_layout(height=980, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_dual, use_container_width=True, key="fig_tab1_dual")

        elif "Raw Engineering" in tab1_view:
            fig = make_subplots(
                rows=4, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.06,
                subplot_titles=(
                    "1. Hydraulic Pressure Profile (PSI)",
                    "2. Electrical Power & Speed Parameters (V, A, Hz)",
                    "3. Thermal Heat Profile (°C)",
                    "4. Mechanical Vibration (G's) & VFD Status"
                )
            )

            # Row 1: Pressures
            if "Inp bar/psi" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Inp bar/psi"], name="Intake Pressure (PSI)", line=dict(color="#00bcd4", width=1.5)), row=1, col=1)
            if "Disch pr. Bar/psi" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Disch pr. Bar/psi"], name="Discharge Pressure (PSI)", line=dict(color="#2196f3", width=1.5)), row=1, col=1)
            if "ΔP Head (PSI)" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["ΔP Head (PSI)"], name="ΔP Head (PSI)", line=dict(color="#9c27b0", width=1.5, dash="dot")), row=1, col=1)
            if "WHP (PSI)" in df_plot and df_plot["WHP (PSI)"].max() > 0:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["WHP (PSI)"], name="Wellhead WHP (PSI)", line=dict(color="#4caf50", width=1.2)), row=1, col=1)
            if "FLP (PSI)" in df_plot and df_plot["FLP (PSI)"].max() > 0:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["FLP (PSI)"], name="Flowline FLP (PSI)", line=dict(color="#ff9800", width=1.2)), row=1, col=1)

            # Row 2: Electrical
            if "VSD Amps/Load" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["VSD Amps/Load"], name="VSD Current (A)", line=dict(color="#e91e63", width=1.5)), row=2, col=1)
            if "Volt" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Volt"], name="Voltage (V)", line=dict(color="#ffc107", width=1.2)), row=2, col=1)
            if "Frequency" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Frequency"], name="Frequency (Hz)", line=dict(color="#3f51b5", width=1.2, dash="dash")), row=2, col=1)
            if "Leak Current Ct" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Leak Current Ct"], name="Leakage Current (mA)", line=dict(color="#f44336", width=1.0)), row=2, col=1)

            # Row 3: Temperature
            if "Motor temp °C" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Motor temp °C"], name="Motor Temp (°C)", line=dict(color="#f44336", width=1.5)), row=3, col=1)
            if "Int temp °C" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Int temp °C"], name="Intake Temp (°C)", line=dict(color="#03a9f4", width=1.5)), row=3, col=1)
            if "Thermal Elevation (°C)" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Thermal Elevation (°C)"], name="Thermal Elevation ΔT (°C)", line=dict(color="#ff5722", width=1.2, dash="dot")), row=3, col=1)

            # Row 4: Vibration
            if "Vibration G's-Vx" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Vibration G's-Vx"], name="Vibration (G)", line=dict(color="#e91e63", width=1.5)), row=4, col=1)
            if "VFD STS" in df_plot:
                fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["VFD STS"], name="VFD Running Status", line=dict(color="#8bc34a", width=1.0)), row=4, col=1)

            fig.update_layout(height=950, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True, key="fig_tab1_raw")

        elif "Normalized" in tab1_view:
            norm_cols = [c for c in df_plot.columns if c.startswith("norm_")]
            if not norm_cols:
                st.warning("No normalized features found. Please run categorization script first.")
            else:
                fig_norm = make_subplots(
                    rows=4, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.06,
                    subplot_titles=(
                        "1. Normalized Hydraulic Space [0, 1]",
                        "2. Normalized Electrical Space [0, 1]",
                        "3. Normalized Thermal Space [0, 1]",
                        "4. Normalized Mechanical Space [0, 1]"
                    )
                )
                # Hydraulics
                for c in ["norm_Inp_bar_psi", "norm_Disch_pr_Bar_psi", "norm_Delta_P_PSI", "norm_WHP_PSI"]:
                    if c in df_plot:
                        fig_norm.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot[c], name=c.replace("norm_", "")), row=1, col=1)
                # Electrical
                for c in ["norm_VSD_Amps_Load", "norm_Volt", "norm_Frequency", "norm_Power_kVA"]:
                    if c in df_plot:
                        fig_norm.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot[c], name=c.replace("norm_", "")), row=2, col=1)
                # Thermal
                for c in ["norm_Motor_temp_C", "norm_Int_temp_C", "norm_Thermal_Elevation_C"]:
                    if c in df_plot:
                        fig_norm.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot[c], name=c.replace("norm_", "")), row=3, col=1)
                # Mechanical
                for c in ["norm_Vibration_G_s_Vx", "norm_Torque_Proxy_A_Hz"]:
                    if c in df_plot:
                        fig_norm.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot[c], name=c.replace("norm_", "")), row=4, col=1)

                fig_norm.update_layout(
                    height=950,
                    hovermode="x unified",
                    yaxis=dict(range=[-0.05, 1.05]),
                    yaxis2=dict(range=[-0.05, 1.05]),
                    yaxis3=dict(range=[-0.05, 1.05]),
                    yaxis4=dict(range=[-0.05, 1.05])
                )
                st.plotly_chart(fig_norm, use_container_width=True, key="fig_tab1_norm")

        else: # Derived Physics Dynamics
            fig_phys = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                subplot_titles=(
                    "1. Differential Head ΔP (Discharge - Intake) [PSI]",
                    "2. Mechanical Torque Proxy (Amps / Hz) & Apparent Power (kVA)",
                    "3. Motor Thermal Elevation ΔT (Motor - Intake) [°C]"
                )
            )
            if "ΔP Head (PSI)" in df_plot:
                fig_phys.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["ΔP Head (PSI)"], name="ΔP Head (PSI)", line=dict(color="#2196f3", width=1.5)), row=1, col=1)
            if "Torque Proxy (A/Hz)" in df_plot:
                fig_phys.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Torque Proxy (A/Hz)"], name="Torque Proxy (A/Hz)", line=dict(color="#ff9800", width=1.5)), row=2, col=1)
            if "Power Proxy (kVA)" in df_plot:
                fig_phys.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Power Proxy (kVA)"], name="Power (kVA)", line=dict(color="#9c27b0", width=1.2, dash="dot")), row=2, col=1)
            if "Thermal Elevation (°C)" in df_plot:
                fig_phys.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Thermal Elevation (°C)"], name="Thermal Elevation (°C)", line=dict(color="#f44336", width=1.5)), row=3, col=1)

            fig_phys.update_layout(height=800, hovermode="x unified")
            st.plotly_chart(fig_phys, use_container_width=True, key="fig_tab1_phys")

    # =============================================================
    # TAB 2: Custom Multi-Sensor Overlay with Range Slider
    # =============================================================
    with tab2:
        st.subheader("Custom Multi-Sensor Comparison Overlay")
        st.caption("Select any combination of sensors to compare on an interactive multi-axis timeline with range slider.")
        
        col_ov1, col_ov2 = st.columns([3, 1])
        with col_ov2:
            scale_mode = st.radio("Scaling Mode", ["Raw Units (Individual)", "Normalized [0, 1] (Aligned Scale)"], horizontal=True)

        with col_ov1:
            available_cols = [c for c in df_plot.columns if c not in ["Report_DateTime", "File_DateTime", "Wells", "Cluster", "Source_File", "Report_ID"]]
            default_selected = [c for c in ["Inp bar/psi", "Disch pr. Bar/psi", "VSD Amps/Load", "Motor temp °C"] if c in available_cols]
            selected_sensors = st.multiselect("Select Sensors to Plot", available_cols, default=default_selected)
        
        if selected_sensors:
            overlay_fig = go.Figure()
            for s in selected_sensors:
                if "Normalized" in scale_mode:
                    # Look for corresponding norm_ column or dynamically normalize
                    norm_col_cand = f"norm_{clean_col_key(s).replace(' ', '_').replace('/', '_').replace('°', '').replace('.', '').replace('(', '').replace(')', '').replace('-', '_')}"
                    if norm_col_cand in df_plot:
                        y_vals = df_plot[norm_col_cand]
                        s_name = f"{s} [Norm 0-1]"
                    else:
                        s_min, s_max = df_plot[s].min(), df_plot[s].max()
                        y_vals = (df_plot[s] - s_min) / (s_max - s_min) if s_max > s_min else np.zeros(len(df_plot))
                        s_name = f"{s} [Norm 0-1]"
                else:
                    y_vals = df_plot[s]
                    s_name = s

                overlay_fig.add_trace(go.Scatter(
                    x=df_plot["Report_DateTime"],
                    y=y_vals,
                    name=s_name,
                    mode="lines"
                ))
            overlay_fig.update_layout(
                title=f"Overlay Timeline for {selected_well_id} ({scale_mode})",
                xaxis=dict(
                    title="Timestamp",
                    rangeslider=dict(visible=True),
                    type="date"
                ),
                yaxis=dict(title="Normalized Scale [0, 1]" if "Normalized" in scale_mode else "Engineering Value"),
                hovermode="x unified",
                height=650
            )
            st.plotly_chart(overlay_fig, use_container_width=True, key="fig_tab2_overlay")
        else:
            st.info("Select one or more sensors above to render the overlay chart.")

    # =============================================================
    # TAB 3: Statistical EDA & Correlations
    # =============================================================
    with tab3:
        st.subheader("Statistical Distributions & Sensor Correlations")
        stat_scope = st.radio("Dataset Scope", ["Raw Engineering Sensors", "Normalized ML Features"], horizontal=True)
        col_stat1, col_stat2 = st.columns([1, 1])

        if stat_scope == "Raw Engineering Sensors":
            sensor_cols = [s for s in STANDARD_SENSORS if s in df_filtered.columns]
        else:
            sensor_cols = [c for c in df_filtered.columns if c.startswith("norm_")]

        # Pre-calculate active columns, units, and dynamic interpreter for Tab 3
        active_sensor_cols = [c for c in sensor_cols if df_filtered[c].std() > 1e-6]
        unmonitored_cols = [c for c in sensor_cols if c not in active_sensor_cols]
        clean_names = [c.replace("norm_", "") for c in active_sensor_cols]

        def get_unit(name):
            nl = name.lower()
            if "freq" in nl: return "Hz"
            if "amp" in nl or "load" in nl: return "A"
            if "volt" in nl: return "V"
            if "temp" in nl: return "°C"
            if "vib" in nl: return "G"
            if any(k in nl for k in ["inp", "disch", "whp", "flp", "ap", "psi"]): return "PSI"
            if "ct" in nl or "current" in nl: return "mA"
            if "flow" in nl or "bpd" in nl: return "BPD"
            return ""

        def dynamically_analyze_pair(col_a, col_b, r_val, df_data, well_id):
            raw_a = col_a.replace("norm_", "")
            raw_b = col_b.replace("norm_", "")
            u_a = get_unit(raw_a)
            u_b = get_unit(raw_b)

            s_a = df_data[raw_a] if raw_a in df_data.columns else df_data[col_a]
            s_b = df_data[raw_b] if raw_b in df_data.columns else df_data[col_b]

            med_a = float(s_a.median())
            med_b = float(s_b.median())
            std_a = float(s_a.std())
            std_b = float(s_b.std())

            slope = (r_val * (std_b / std_a)) if std_a > 1e-6 else 0.0
            sensitivity_str = f"{slope:+.2f} {u_b}/{u_a}".strip() if u_a and u_b else f"{slope:+.2f}"

            ca = raw_a.lower()
            cb = raw_b.lower()

            if ("freq" in ca and "disch" in cb) or ("freq" in cb and "disch" in ca):
                f_val = med_a if "freq" in ca else med_b
                p_val = med_b if "freq" in ca else med_a
                if r_val >= 0.50:
                    risk = "🟢 OPTIMAL LIFT"
                    summary = f"Speed ({f_val:.1f} Hz) lifts discharge head ({p_val:.1f} PSI) at {abs(slope):.1f} PSI/Hz."
                    impact = f"High lift efficiency (+{abs(slope):.1f} PSI/Hz). Impellers are healthy."
                else:
                    risk = "🔴 DECOUPLED / OPEX RISK"
                    summary = f"Discharge ({p_val:.1f} PSI) fails to track speed ({f_val:.1f} Hz) (r = {r_val:+.2f})."
                    impact = "Wasted electricity: High kWh without oil lift. Check for gas lock or scale."

            elif ("freq" in ca and ("amp" in cb or "load" in cb)) or ("freq" in cb and ("amp" in ca or "load" in ca)):
                f_val = med_a if "freq" in ca else med_b
                a_val = med_b if "freq" in ca else med_a
                if r_val >= 0.50:
                    risk = "🟢 NORMAL LOAD"
                    summary = f"Motor load ({a_val:.1f} A) scales with speed ({f_val:.1f} Hz) at {abs(slope):.2f} A/Hz."
                    impact = f"Normal fluid throughput. Power of {a_val:.1f} A matches hydraulic load."
                else:
                    risk = "🔴 UNDERLOAD RISK"
                    summary = f"Speed is {f_val:.1f} Hz but current ({a_val:.1f} A) is decoupled (r = {r_val:+.2f})."
                    impact = "Fluid starvation / gas dry-run. Risk of sudden underload trip."

            elif ("freq" in ca and "volt" in cb) or ("freq" in cb and "volt" in ca):
                v_val = med_b if "volt" in cb else med_a
                f_val = med_a if "freq" in ca else med_b
                if r_val >= 0.70:
                    risk = "🟢 VFD REGULATED"
                    summary = f"VFD supplies {v_val:.0f} V at {f_val:.1f} Hz (Ratio: {v_val/max(1, f_val):.1f} V/Hz)."
                    impact = "Optimal surface VFD regulation with constant magnetic flux."
                else:
                    risk = "🟡 VOLTAGE FLUCTUATION"
                    summary = f"Voltage ({v_val:.0f} V) fluctuates non-linearly with frequency ({f_val:.1f} Hz)."
                    impact = "Surface grid voltage sag. Inspect transformer tap setting."

            elif ("freq" in ca and "inp" in cb) or ("freq" in cb and "inp" in ca):
                p_in = med_b if "inp" in cb else med_a
                f_val = med_a if "freq" in ca else med_b
                if r_val <= -0.20:
                    risk = "🟢 HEALTHY DRAWDOWN"
                    summary = f"Speed ({f_val:.1f} Hz) draws reservoir intake ({p_in:.1f} PSI) down by {abs(slope):.1f} PSI/Hz."
                    impact = "Responsive IPR drawdown: Well responds well to frequency adjustments."
                else:
                    risk = "🟡 CONSTANT COLUMN"
                    summary = f"Intake ({p_in:.1f} PSI) remains steady despite speed changes at {f_val:.1f} Hz."
                    impact = "High reservoir support or well operates near static level."

            elif ("inp" in ca and "disch" in cb) or ("inp" in cb and "disch" in ca):
                p_in = med_a if "inp" in ca else med_b
                p_out = med_b if "disch" in cb else med_a
                delta_p = p_out - p_in
                if r_val >= 0.40:
                    risk = "🟢 STABLE HEAD"
                    summary = f"Intake ({p_in:.1f} PSI) & Discharge ({p_out:.1f} PSI) track steadily (ΔP = {delta_p:.1f} PSI)."
                    impact = f"Stable pump head ({delta_p:.1f} PSI). Pump operates in normal capacity range."
                else:
                    risk = "🟡 PRESSURE DIVERGENCE"
                    summary = f"Intake and Discharge pressures fluctuate asynchronously (r = {r_val:+.2f})."
                    impact = "Hydraulic instability: Check for flowline backpressure or gas slugging."

            elif (("amp" in ca or "load" in ca) and "motor temp" in cb) or (("amp" in cb or "load" in cb) and "motor temp" in ca):
                a_val = med_a if ("amp" in ca or "load" in ca) else med_b
                t_val = med_b if "temp" in cb else med_a
                if r_val >= 0.35 and t_val < 85.0:
                    risk = "🟢 NORMAL HEATING"
                    summary = f"Motor temp ({t_val:.1f}°C) tracks load ({a_val:.1f} A) via standard I²R heat."
                    impact = "Fluid velocity past motor jacket is sufficient for convective cooling."
                elif t_val >= 85.0:
                    risk = "🔴 THERMAL BURNOUT RISK"
                    summary = f"Motor temperature is elevated at {t_val:.1f}°C under {a_val:.1f} A load."
                    impact = "Severe thermal wear: Risk of $200k+ stator burnout and workover."
                else:
                    risk = "🟡 STABLE TEMPERATURE"
                    summary = f"Motor temp ({t_val:.1f}°C) and current ({a_val:.1f} A) in thermal equilibrium."
                    impact = "Thermal insulation within safe margin; monitor fluid level."

            elif (("amp" in ca or "load" in ca) and "vib" in cb) or (("amp" in cb or "load" in cb) and "vib" in ca):
                a_val = med_a if ("amp" in ca or "load" in ca) else med_b
                v_val = med_b if "vib" in cb else med_a
                if r_val >= 0.35 and v_val > 0.15:
                    risk = "🔴 SOLIDS ABRASION RISK"
                    summary = f"Vibration ({v_val:.3f} G) surges with current ({a_val:.1f} A) at +{slope:.3f} G/A."
                    impact = "Sand / solids ingestion: Abrasive particles erode impellers and cut run-life."
                else:
                    risk = "🟢 SMOOTH ROTOR"
                    summary = f"Vibration is low ({v_val:.3f} G) and unaffected by current changes ({a_val:.1f} A)."
                    impact = "Clean fluid with balanced rotor. Maximizes pump life (MTBF > 3 yrs)."

            elif ("vib" in ca and "freq" in cb) or ("vib" in cb and "freq" in ca):
                v_val = med_a if "vib" in ca else med_b
                f_val = med_b if "freq" in cb else med_a
                if r_val >= 0.45:
                    risk = "🟡 SPEED RESONANCE"
                    summary = f"Vibration ({v_val:.3f} G) increases with speed ({f_val:.1f} Hz) at +{slope:.4f} G/Hz."
                    impact = "Speed-dependent vibration: Set VFD skip bands to avoid resonant speeds."
                else:
                    risk = "🟢 BALANCED SHAFT"
                    summary = f"Vibration remains minimal ({v_val:.3f} G) across all speeds (Median: {f_val:.1f} Hz)."
                    impact = "Excellent mechanical balance throughout operating range."

            elif ("motor temp" in ca and "int temp" in cb) or ("motor temp" in cb and "int temp" in ca):
                t_mot = med_a if "motor temp" in ca else med_b
                t_int = med_b if "int temp" in cb else med_a
                delta_t = t_mot - t_int
                if delta_t <= 25.0:
                    risk = "🟢 HEALTHY THERMAL RISE"
                    summary = f"Motor ({t_mot:.1f}°C) & Intake ({t_int:.1f}°C) maintain healthy ΔT = {delta_t:.1f}°C."
                    impact = f"Motor heat ({delta_t:.1f}°C rise) is completely dissipated by fluid flow."
                else:
                    risk = "🔴 HIGH MOTOR HEAT"
                    summary = f"High motor thermal rise (ΔT = {delta_t:.1f}°C: Motor {t_mot:.1f}°C vs Intake {t_int:.1f}°C)."
                    impact = "Internal heat accumulation: Possible lubrication breakdown or scale fouling."

            else:
                if abs(r_val) >= 0.60:
                    risk = "🟢 SYNCHRONOUS COUPLING" if r_val > 0 else "🔵 INVERSE COUPLING"
                    summary = f"{raw_a} ({med_a:.2f} {u_a}) and {raw_b} ({med_b:.2f} {u_b}) move in lockstep (r = {r_val:+.2f})."
                    impact = f"Changes in {raw_a} propagate at {sensitivity_str} into {raw_b}."
                elif abs(r_val) >= 0.30:
                    risk = "🟡 MODERATE COUPLING"
                    summary = f"{raw_a} ({med_a:.2f} {u_a}) and {raw_b} ({med_b:.2f} {u_b}) show moderate interaction (r = {r_val:+.2f})."
                    impact = f"Secondary operational interdependence ({sensitivity_str})."
                else:
                    risk = "⚪ INDEPENDENT"
                    summary = f"{raw_a} ({med_a:.2f} {u_a}) and {raw_b} ({med_b:.2f} {u_b}) operate independently (r = {r_val:+.2f})."
                    impact = "Zero cross-channel interference; channels operate independently."

            return risk, sensitivity_str, summary, impact

        corr_matrix = df_filtered[active_sensor_cols].corr() if len(active_sensor_cols) > 1 else pd.DataFrame()

        with col_stat1:
            st.markdown(f"#### 📊 {stat_scope} Distribution Summary")
            if sensor_cols:
                stats_df = df_filtered[sensor_cols].describe().T[["min", "mean", "50%", "max", "std"]]
                stats_df.rename(columns={"50%": "median"}, inplace=True)
                st.dataframe(stats_df.style.format("{:.3f}"), use_container_width=True)

            # =========================================================
            # Dedicated Live Hover & Interactive Guide Box (Left Column)
            # =========================================================
            st.markdown("---")
            st.markdown("#### 🎯 Live Heatmap Hover Guide & Highlights")
            st.caption("Move your mouse cursor across any box in the heatmap to see instant live physical sensitivity and business impact.")

            if len(active_sensor_cols) > 1:
                # Highlight top key pairs automatically
                st.markdown("""
                <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 12px; margin-top: 4px;">
                    <div style="font-size: 13px; font-weight: 700; color: #38BDF8; margin-bottom: 6px;">⚡ How to Explore Correlations:</div>
                    <ul style="font-size: 12px; color: #E2E8F0; margin: 0; padding-left: 18px; line-height: 1.6;">
                        <li><strong>Hover over any square:</strong> The exact correlation, live rate (sensitivity), and commercial impact pop up immediately.</li>
                        <li><strong>Dark Red (r &gt; +0.70):</strong> Strong direct lockstep relationship.</li>
                        <li><strong>Dark Blue (r &lt; -0.70):</strong> Strong inverse relationship.</li>
                        <li><strong>Scroll down:</strong> View the comprehensive <em>Pairwise Parameter Diagnostic Table</em> with search and CSV export.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

        with col_stat2:
            st.markdown(f"#### 🔥 Pearson Correlation Heatmap ({stat_scope})")
            if len(active_sensor_cols) > 1:
                # Build customdata grid matching EXACT matrix dimensions (N x N)
                custom_data_grid = []
                for i, col_y in enumerate(active_sensor_cols):
                    row_data = []
                    for j, col_x in enumerate(active_sensor_cols):
                        r_val = float(corr_matrix.loc[col_y, col_x])
                        if col_y == col_x:
                            row_data.append(["1.00 (Self)", "⚪ BASELINE SELF", f"{clean_names[j]} compared against itself", "Self-correlation baseline"])
                        else:
                            risk, sens, summary, impact = dynamically_analyze_pair(
                                col_y, col_x, r_val, df_filtered, selected_well_id
                            )
                            row_data.append([sens, risk, summary, impact])
                    custom_data_grid.append(row_data)

                # Render interactive Plotly Heatmap with exact live hover inspection
                heatmap_fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=clean_names,
                    y=clean_names,
                    colorscale="RdBu_r",
                    zmin=-1,
                    zmax=1,
                    text=np.around(corr_matrix.values, decimals=2),
                    texttemplate="%{text:.2f}",
                    textfont={"size": 11},
                    customdata=custom_data_grid,
                    hovertemplate=(
                        "<b>⚡ %{y}</b>  ↔  <b>%{x}</b><br><br>"
                        "<b>📊 Correlation (r):</b> %{z:+.2f}<br>"
                        "<b>⚡ Sensitivity:</b> %{customdata[0]}<br>"
                        "<b>🚦 Status:</b> %{customdata[1]}<br><br>"
                        "<b>🔬 Physics:</b> %{customdata[2]}<br>"
                        "<b>💰 Business Impact:</b> %{customdata[3]}"
                        "<extra></extra>"
                    )
                ))

                heatmap_fig.update_layout(
                    height=530,
                    margin=dict(l=20, r=20, t=30, b=20),
                    hoverlabel=dict(
                        bgcolor="rgba(15, 23, 42, 0.95)",
                        bordercolor="#38BDF8",
                        font_size=12,
                        font_family="Inter, sans-serif",
                        font_color="#F8FAFC",
                        align="left"
                    )
                )

                st.plotly_chart(heatmap_fig, use_container_width=True, key="fig_stat_heatmap")
                if unmonitored_cols:
                    st.caption(f"ℹ️ *Note:* Constant / unmonitored sensors with zero variance (`{', '.join([c.replace('norm_', '') for c in unmonitored_cols])}`) are excluded from correlation because Pearson correlation requires non-zero variance (Std Dev > 0).")
            else:
                st.info("Insufficient varying sensors to compute correlation matrix.")

        # =============================================================
        # Dynamic Real-Time Correlation Business & Physics Interpretation
        # =============================================================
        st.markdown("---")
        st.markdown("### 💡 Live Correlation & Business Impact Summary")
        st.caption("Automated physics-based interpretation of how current sensor relationships impact production, power efficiency, and ESP run-life.")

        # Helper to safely retrieve correlation between two base names
        def get_pair_corr(c_matrix, name1, name2):
            for c1 in c_matrix.columns:
                if name1.lower() in c1.lower():
                    for c2 in c_matrix.columns:
                        if name2.lower() in c2.lower() and c1 != c2:
                            val = c_matrix.loc[c1, c2]
                            if not np.isnan(val):
                                return float(val), c1, c2
            return None, name1, name2

        if len(active_sensor_cols) > 1:
            c_mat = df_filtered[active_sensor_cols].corr()
            c_card1, c_card2, c_card3 = st.columns(3)

            # --- Card 1: Hydraulic Lift & Affinity Coupling ---
            with c_card1:
                st.markdown("#### 🌊 1. Hydraulic Head Coupling")
                r_val, k1, k2 = get_pair_corr(c_mat, "freq", "disch")
                if r_val is not None:
                    if r_val >= 0.65:
                        status_badge = "🟢 **Optimal Coupling**"
                        interp = f"Speed ({k1}) directly drives discharge head ({k2}) with $r = +{r_val:.2f}$. Affinity laws are intact."
                        biz_action = "✅ **Business Impact**: Efficient power-to-head conversion. Pump stages are healthy."
                    elif r_val >= 0.25:
                        status_badge = "🟡 **Moderate Coupling**"
                        interp = f"Moderate lift response ($r = +{r_val:.2f}$). Fluctuations in wellhead backpressure or fluid density present."
                        biz_action = "🔍 **Business Impact**: Monitor choke settings to optimize barrel lifting cost."
                    else:
                        status_badge = "🔴 **Decoupling Alert**"
                        interp = f"Speed and discharge head are decoupled ($r = {r_val:.2f}$). Increasing RPM fails to increase pressure."
                        biz_action = "⚠️ **Business Risk**: Impeller scale wear or gas locking. High risk of wasted electrical OPEX."
                    st.info(f"{status_badge}\n\n**Correlation ($r$):** `{r_val:+.2f}`\n\n{interp}\n\n{biz_action}")
                else:
                    st.info("ℹ️ Speed vs Discharge data unavailable in selected window.")

            # --- Card 2: Electrical Load & Motor Cooling ---
            with c_card2:
                st.markdown("#### ⚡ 2. Electrical & Fluid Cooling")
                r_curr_temp, k_c, k_t = get_pair_corr(c_mat, "amp", "motor temp")
                r_freq_amp, _, _ = get_pair_corr(c_mat, "freq", "amp")
                if r_curr_temp is not None:
                    if r_curr_temp >= 0.45:
                        status_badge = "🟢 **Normal Thermal Heating**"
                        interp = f"Motor temperature tracks current draw ($r = +{r_curr_temp:.2f}$) via standard ohmic ($I^2 R$) dissipation."
                        biz_action = "✅ **Business Impact**: Cooling fluid flow past the motor jacket is sufficient."
                    elif r_curr_temp <= 0.10:
                        status_badge = "🔴 **Cooling Decoupling Risk**"
                        interp = f"Temperature and current are uncorrelated ($r = {r_curr_temp:+.2f}$). Motor heating independently of load."
                        biz_action = "⚠️ **Business Risk**: Fluid starvation / dry-run. Stator winding burnout risk ($150k-$300k workover cost)."
                    else:
                        status_badge = "🟡 **Stable Thermal State**"
                        interp = f"Steady-state thermal equilibrium ($r = {r_curr_temp:+.2f}$). Minor load-temperature sensitivity."
                        biz_action = "ℹ️ **Business Impact**: Operating within safe thermal insulation class."
                    st.info(f"{status_badge}\n\n**Correlation ($r$):** `{r_curr_temp:+.2f}`\n\n{interp}\n\n{biz_action}")
                else:
                    st.info("ℹ️ Current vs Temperature data unavailable in selected window.")

            # --- Card 3: Mechanical Friction & Solids Slugging ---
            with c_card3:
                st.markdown("#### ⚙️ 3. Mechanical & Solids Friction")
                r_vib_amp, k_v, k_a = get_pair_corr(c_mat, "vib", "amp")
                if r_vib_amp is not None:
                    if r_vib_amp >= 0.40:
                        status_badge = "🔴 **Abrasive Solids Slugging**"
                        interp = f"Vibration surges correlate positively with current spikes ($r = +{r_vib_amp:.2f}$). Solids friction drag."
                        biz_action = "⚠️ **Business Risk**: Sand / solids ingestion. Accelerated pump stage and bearing abrasive wear."
                    elif r_vib_amp <= -0.20:
                        status_badge = "🟡 **Mechanical Decoupling**"
                        interp = f"Vibration fluctuations independent of load ($r = {r_vib_amp:+.2f}$). Potential mechanical imbalance."
                        biz_action = "🔍 **Business Impact**: Check for electrical harmonics or shaft eccentricity."
                    else:
                        status_badge = "🟢 **Smooth Mechanical Profile**"
                        interp = f"Low vibration-load cross-coupling ($r = {r_vib_amp:+.2f}$). Clean fluid passing through pump."
                        biz_action = "✅ **Business Impact**: Extended ESP run-life (MTBF > 3 years)."
                    st.info(f"{status_badge}\n\n**Correlation ($r$):** `{r_vib_amp:+.2f}`\n\n{interp}\n\n{biz_action}")
                else:
                    st.info("ℹ️ Vibration vs Current data unavailable in selected window.")

        # =============================================================
        # Dynamic Real-Time Pairwise Parameter Diagnostic Table
        # =============================================================
        st.markdown("---")
        st.markdown("### 📋 Dynamic Pairwise Parameter Diagnostic & Business Impact Table")
        st.caption("Live, data-driven physical sensitivity and commercial risk analysis calculated directly from current well telemetry and calibration baselines.")

        if len(active_sensor_cols) > 1:
            # Helper to deduce sensor engineering unit
            def get_unit(name):
                nl = name.lower()
                if "freq" in nl: return "Hz"
                if "amp" in nl or "load" in nl: return "A"
                if "volt" in nl: return "V"
                if "temp" in nl: return "°C"
                if "vib" in nl: return "G"
                if any(k in nl for k in ["inp", "disch", "whp", "flp", "ap", "psi"]): return "PSI"
                if "ct" in nl or "current" in nl: return "mA"
                if "flow" in nl or "bpd" in nl: return "BPD"
                return ""

            # Dynamic pairwise interpreter
            def dynamically_analyze_pair(col_a, col_b, r_val, df_data, well_id):
                raw_a = col_a.replace("norm_", "")
                raw_b = col_b.replace("norm_", "")
                u_a = get_unit(raw_a)
                u_b = get_unit(raw_b)

                # Compute live stats from filtered dataframe
                s_a = df_data[raw_a] if raw_a in df_data.columns else df_data[col_a]
                s_b = df_data[raw_b] if raw_b in df_data.columns else df_data[col_b]

                med_a = float(s_a.median())
                med_b = float(s_b.median())
                std_a = float(s_a.std())
                std_b = float(s_b.std())

                # Live sensitivity slope: ΔB / ΔA = r * (std_B / std_A)
                slope = (r_val * (std_b / std_a)) if std_a > 1e-6 else 0.0
                sensitivity_str = f"{slope:+.2f} {u_b}/{u_a}".strip() if u_a and u_b else f"{slope:+.2f}"

                ca = raw_a.lower()
                cb = raw_b.lower()

                # Dynamic classification based on physical domains and live numbers
                # 1. Frequency vs Discharge Head
                if ("freq" in ca and "disch" in cb) or ("freq" in cb and "disch" in ca):
                    f_val = med_a if "freq" in ca else med_b
                    p_val = med_b if "freq" in ca else med_a
                    if r_val >= 0.60:
                        risk = "🟢 LOW RISK"
                        summary = f"At {f_val:.1f} Hz, pump generates {p_val:.1f} PSI discharge with direct +{abs(slope):.1f} PSI/Hz lift response."
                        impact = f"High electrical efficiency: Each Hz added produces +{abs(slope):.1f} PSI head. Stage impellers are healthy."
                    else:
                        risk = "🔴 HIGH OPEX RISK"
                        summary = f"Pump speed is running at {f_val:.1f} Hz, but discharge pressure ({p_val:.1f} PSI) is failing to track speed (r = {r_val:+.2f})."
                        impact = "Wasted electricity OPEX: Motor consumes high kWh power without generating proportional oil lift. Check for gas locking or scale wear."

                # 2. Frequency vs Motor Current / Load
                elif ("freq" in ca and ("amp" in cb or "load" in cb)) or ("freq" in cb and ("amp" in ca or "load" in ca)):
                    f_val = med_a if "freq" in ca else med_b
                    a_val = med_b if "freq" in ca else med_a
                    if r_val >= 0.55:
                        risk = "🟢 LOW RISK"
                        summary = f"Motor load ({a_val:.1f} A) scales smoothly with pump speed ({f_val:.1f} Hz) at {abs(slope):.2f} A/Hz."
                        impact = f"Normal fluid throughput. Power draw of {a_val:.1f} A matches pump hydraulic load."
                    else:
                        risk = "🔴 UNDERLOAD RISK"
                        summary = f"Motor running at {f_val:.1f} Hz but current ({a_val:.1f} A) is decoupled from speed (r = {r_val:+.2f})."
                        impact = "Pump-off / gas dry-run warning: Low fluid loading creates high risk of sudden VFD underload trip."

                # 3. Frequency vs Voltage
                elif ("freq" in ca and "volt" in cb) or ("freq" in cb and "volt" in ca):
                    v_val = med_b if "volt" in cb else med_a
                    f_val = med_a if "freq" in ca else med_b
                    if r_val >= 0.70:
                        risk = "🟢 LOW RISK"
                        summary = f"VFD supplies {v_val:.0f} V at {f_val:.1f} Hz (Ratio: {v_val/max(1, f_val):.1f} V/Hz)."
                        impact = "Optimal surface electrical drive regulation with stable magnetic flux and zero transformer overload."
                    else:
                        risk = "🟡 MONITOR"
                        summary = f"Voltage ({v_val:.0f} V) fluctuates non-linearly with frequency ({f_val:.1f} Hz)."
                        impact = "Potential surface grid voltage fluctuation. Check transformer tap setting to prevent drive tripping."

                # 4. Frequency vs Intake Pressure
                elif ("freq" in ca and "inp" in cb) or ("freq" in cb and "inp" in ca):
                    p_in = med_b if "inp" in cb else med_a
                    f_val = med_a if "freq" in ca else med_b
                    if r_val <= -0.25:
                        risk = "🟢 LOW RISK"
                        summary = f"Increasing speed to {f_val:.1f} Hz pulls reservoir intake down ({p_in:.1f} PSI) by {abs(slope):.1f} PSI/Hz."
                        impact = "Healthy reservoir drawdown (IPR). The well is actively responding to speed optimization."
                    else:
                        risk = "🟡 MONITOR"
                        summary = f"Intake pressure ({p_in:.1f} PSI) remains flat despite speed adjustments at {f_val:.1f} Hz."
                        impact = "Reservoir inflow is high or constant fluid level. Well is capable of higher production rate if boosted."

                # 5. Intake Pressure vs Discharge Pressure
                elif ("inp" in ca and "disch" in cb) or ("inp" in cb and "disch" in ca):
                    p_in = med_a if "inp" in ca else med_b
                    p_out = med_b if "disch" in cb else med_a
                    delta_p = p_out - p_in
                    if r_val >= 0.40:
                        risk = "🟢 LOW RISK"
                        summary = f"Intake ({p_in:.1f} PSI) and Discharge ({p_out:.1f} PSI) track steadily, maintaining ΔP = {delta_p:.1f} PSI head."
                        impact = f"Stable pump head generation ({delta_p:.1f} PSI). Pump operates within its recommended hydraulic envelope."
                    else:
                        risk = "🟡 MONITOR"
                        summary = f"Intake and Discharge pressures are fluctuating asynchronously (r = {r_val:+.2f})."
                        impact = "Hydraulic instability: Check for fluctuating surface flowline backpressure or gas slugging."

                # 6. Motor Current vs Motor Temperature
                elif (("amp" in ca or "load" in ca) and "motor temp" in cb) or (("amp" in cb or "load" in cb) and "motor temp" in ca):
                    a_val = med_a if ("amp" in ca or "load" in ca) else med_b
                    t_val = med_b if "temp" in cb else med_a
                    if r_val >= 0.35 and t_val < 85.0:
                        risk = "🟢 LOW RISK"
                        summary = f"Motor temp ({t_val:.1f}°C) rises normally with current draw ({a_val:.1f} A) via standard electrical heating."
                        impact = "Fluid velocity past motor jacket is sufficient for continuous convective cooling; zero winding damage."
                    elif t_val >= 85.0:
                        risk = "🔴 CRITICAL THERMAL RISK"
                        summary = f"Motor temperature is elevated at {t_val:.1f}°C under {a_val:.1f} A load."
                        impact = "Severe motor winding thermal degradation: Risk of $200,000+ premature ESP burnout and replacement workover."
                    else:
                        risk = "🟡 MONITOR"
                        summary = f"Motor temp ({t_val:.1f}°C) and current ({a_val:.1f} A) are operating in steady thermal equilibrium."
                        impact = "Thermal insulation within safe margin; monitor fluid level to maintain cooling flow."

                # 7. Motor Current vs Vibration
                elif (("amp" in ca or "load" in ca) and "vib" in cb) or (("amp" in cb or "load" in cb) and "vib" in ca):
                    a_val = med_a if ("amp" in ca or "load" in ca) else med_b
                    v_val = med_b if "vib" in cb else med_a
                    if r_val >= 0.35 and v_val > 0.15:
                        risk = "🔴 HIGH ABRASION RISK"
                        summary = f"Vibration surges (Median {v_val:.3f} G) correlate with current spikes ({a_val:.1f} A) at +{slope:.3f} G/A."
                        impact = "Sand / solids ingestion active: Abrasive particles drag on pump impellers, accelerating bearing wear and cutting run-life in half."
                    else:
                        risk = "🟢 LOW RISK"
                        summary = f"Vibration is low ({v_val:.3f} G) and unaffected by current load changes ({a_val:.1f} A)."
                        impact = "Clean fluid production with smooth rotor balance. Maximizes Mean Time Between Failures (MTBF > 3 years)."

                # 8. Vibration vs Frequency
                elif ("vib" in ca and "freq" in cb) or ("vib" in cb and "freq" in ca):
                    v_val = med_a if "vib" in ca else med_b
                    f_val = med_b if "freq" in cb else med_a
                    if r_val >= 0.45:
                        risk = "🟡 MONITOR"
                        summary = f"Vibration ({v_val:.3f} G) increases with higher pump speed ({f_val:.1f} Hz) at +{slope:.4f} G/Hz."
                        impact = "Speed-dependent vibration: Set VFD frequency skip bands to avoid mechanical resonance speeds."
                    else:
                        risk = "🟢 LOW RISK"
                        summary = f"Vibration remains minimal ({v_val:.3f} G) across all operating frequencies (Median: {f_val:.1f} Hz)."
                        impact = "Excellent mechanical balance throughout the operational speed range."

                # 9. Motor Temp vs Intake Temp
                elif ("motor temp" in ca and "int temp" in cb) or ("motor temp" in cb and "int temp" in ca):
                    t_mot = med_a if "motor temp" in ca else med_b
                    t_int = med_b if "int temp" in cb else med_a
                    delta_t = t_mot - t_int
                    if delta_t <= 25.0:
                        risk = "🟢 LOW RISK"
                        summary = f"Motor temp ({t_mot:.1f}°C) and Intake temp ({t_int:.1f}°C) maintain healthy ΔT = {delta_t:.1f}°C thermal rise."
                        impact = f"Internal motor heat generation ({delta_t:.1f}°C rise) is completely dissipated by reservoir fluid flow."
                    else:
                        risk = "🔴 THERMAL ELEVATION"
                        summary = f"Motor internal heat rise is high (ΔT = {delta_t:.1f}°C: Motor {t_mot:.1f}°C vs Intake {t_int:.1f}°C)."
                        impact = "Internal heat accumulation: Possible lubrication breakdown or scale fouling on motor pothead."

                # 10. Generic Dynamic Fallback
                else:
                    if abs(r_val) >= 0.60:
                        risk = "🟢 LOW RISK" if r_val > 0 else "🔵 INVERSE COUPLING"
                        summary = f"{raw_a} (Median {med_a:.2f} {u_a}) and {raw_b} (Median {med_b:.2f} {u_b}) move synchronously (r = {r_val:+.2f})."
                        impact = f"Changes in {raw_a} propagate at a rate of {sensitivity_str} into {raw_b}."
                    elif abs(r_val) >= 0.30:
                        risk = "🟡 MODERATE COUPLING"
                        summary = f"{raw_a} ({med_a:.2f} {u_a}) and {raw_b} ({med_b:.2f} {u_b}) show moderate interaction (r = {r_val:+.2f})."
                        impact = f"Secondary operational interdependence ({sensitivity_str})."
                    else:
                        risk = "⚪ INDEPENDENT"
                        summary = f"{raw_a} ({med_a:.2f} {u_a}) and {raw_b} ({med_b:.2f} {u_b}) operate independently (r = {r_val:+.2f})."
                        impact = "Zero cross-channel interference; changes in one parameter do not destabilize the other."

                return risk, sensitivity_str, summary, impact

            # Build comprehensive pairwise dataframe
            pairwise_records = []
            n_cols = len(active_sensor_cols)
            c_matrix = df_filtered[active_sensor_cols].corr()

            for i in range(n_cols):
                for j in range(i + 1, n_cols):
                    col1 = active_sensor_cols[i]
                    col2 = active_sensor_cols[j]
                    r = float(c_matrix.loc[col1, col2])
                    if not np.isnan(r):
                        risk, sensitivity, summary, impact = dynamically_analyze_pair(
                            col1, col2, r, df_filtered, selected_well_id
                        )
                        pairwise_records.append({
                            "Parameter Pair": f"{col1.replace('norm_', '')}  ↔  {col2.replace('norm_', '')}",
                            "Correlation (r)": r,
                            "Live Sensitivity": sensitivity,
                            "Commercial Risk": risk,
                            "Executive Summary (Easy to Understand)": summary,
                            "Dynamic Business & Operational Impact": impact
                        })

            if pairwise_records:
                df_pairwise = pd.DataFrame(pairwise_records)
                
                # Filter controls
                col_tbl_f1, col_tbl_f2 = st.columns([1, 2])
                with col_tbl_f1:
                    filter_risk = st.selectbox(
                        "🔍 Filter by Risk Level",
                        ["All Risk Levels", "🔴 HIGH", "🟡 MONITOR", "🟢 LOW RISK"],
                        key="sel_pairwise_risk"
                    )
                with col_tbl_f2:
                    search_kw = st.text_input("🔎 Search by Parameter Name or Keyword", "", key="txt_pairwise_search")

                df_display = df_pairwise.copy()
                if filter_risk != "All Risk Levels":
                    df_display = df_display[df_display["Commercial Risk"].str.contains(filter_risk.replace("All Risk Levels", ""))]
                if search_kw.strip():
                    kw = search_kw.lower().strip()
                    df_display = df_display[
                        df_display["Parameter Pair"].str.lower().str.contains(kw) |
                        df_display["Executive Summary (Easy to Understand)"].str.lower().str.contains(kw) |
                        df_display["Dynamic Business & Operational Impact"].str.lower().str.contains(kw)
                    ]

                # Format correlation column
                st.dataframe(
                    df_display.style.format({"Correlation (r)": "{:+.3f}"}),
                    use_container_width=True,
                    height=450
                )
                
                st.download_button(
                    label="📥 Download Complete Dynamic Correlation & Business Analysis (CSV)",
                    data=df_pairwise.to_csv(index=False).encode("utf-8"),
                    file_name=f"{selected_well_id}_dynamic_correlation_business_analysis.csv",
                    mime="text/csv",
                    key="btn_download_pairwise_csv"
                )

        st.markdown("#### 📦 Outlier & Boxplot Analysis")
        selected_box_sensor = st.selectbox("Select Sensor for Distribution Boxplot", sensor_cols, index=0)
        box_fig = px.box(
            df_filtered,
            y=selected_box_sensor,
            points="outliers",
            title=f"Distribution & Outlier Boxplot: {selected_box_sensor}"
        )
        box_fig.update_layout(height=350)
        st.plotly_chart(box_fig, use_container_width=True, key="fig_stat_box")

    # =============================================================
    # TAB 4: Anomaly & 13-Fault Diagnostics Timeline
    # =============================================================
    with tab4:
        st.subheader("13-Fault Diagnostic & Anomaly Timeline")
        st.caption("Evaluates live physics rules and ML anomaly scoring to track well health and classify fault events over time.")

        engine = get_diagnostic_engine()
        if engine is None:
            st.warning("Diagnostic engine models package not found. Please ensure `models/` is present.")
        else:
            if st.button("🚀 Run 13-Fault Diagnostic Scan on Timeline", type="primary"):
                with st.spinner("Diagnosing telemetry points across selected range..."):
                    # Sample up to 100 points evenly across timeline for performance
                    sample_step = max(1, len(df_filtered) // 100)
                    df_sample = df_filtered.iloc[::sample_step].copy()
                    
                    health_scores = []
                    fault_labels = []
                    statuses = []
                    
                    for _, row in df_sample.iterrows():
                        raw_dict = row.to_dict()
                        eval_res = engine.evaluate_live_telemetry(selected_well_id, raw_dict, verbose=False)
                        diag = eval_res["diagnostic"]
                        health_scores.append(diag["health_score"])
                        fault_labels.append(diag["primary_fault"])
                        statuses.append(diag["status"])
                        
                    df_sample["Health_Score"] = health_scores
                    df_sample["Primary_Fault"] = fault_labels
                    df_sample["Status"] = statuses

                    # Plot Health Score Timeline
                    health_fig = go.Figure()
                    health_fig.add_trace(go.Scatter(
                        x=df_sample["Report_DateTime"],
                        y=df_sample["Health_Score"],
                        mode="lines+markers",
                        name="Health Index (0-100)",
                        line=dict(color="#4caf50", width=2),
                        marker=dict(size=6, color=np.where(df_sample["Health_Score"] < 50, "#f44336", "#4caf50"))
                    ))
                    health_fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Normal Threshold (80)")
                    health_fig.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Critical Threshold (40)")
                    health_fig.update_layout(
                        title=f"Health Index Trajectory for {selected_well_id}",
                        yaxis=dict(title="Health Index (0 - 100)", range=[0, 105]),
                        height=400
                    )
                    st.plotly_chart(health_fig, use_container_width=True, key="fig_tab4_health")

                    # Display Detected Fault Events
                    faults_detected = df_sample[df_sample["Primary_Fault"] != "Normal Operation"]
                    if not faults_detected.empty:
                        st.markdown(f"#### ⚠️ Detected Fault Incidents ({len(faults_detected)} points)")
                        st.dataframe(faults_detected[["Report_DateTime", "Health_Score", "Primary_Fault", "Status", "Inp bar/psi", "Disch pr. Bar/psi", "VSD Amps/Load", "Motor temp °C"]], use_container_width=True)
                    else:
                        st.success("✅ No critical fault conditions detected. Well operated within healthy baseline envelope.")

    # =============================================================
    # TAB 5: Trends & Degradation Analysis (NEW)
    # =============================================================
    with tab5:
        st.subheader("📈 Long-Term Degradation & Trend Analysis")
        st.caption("Analyzes continuous rates of change (slopes) across the selected timeline to identify progressive physical wear.")

        trends_data = compute_trends_and_slopes(df_filtered)
        if not trends_data:
            st.info("Insufficient data points in selected date range to calculate linear trend slopes.")
        else:
            t_col1, t_col2 = st.columns([1, 1])

            with t_col1:
                st.markdown("#### 🧭 Key Trend Slopes (Daily Drift Rates)")
                for k, t_info in trends_data.items():
                    st.markdown(f"""
                    **{t_info['title']}**: `{t_info['slope']} {t_info['unit']}`  
                    *Status:* **{t_info['status']}** | *Net Change:* `{t_info['total_change']} {t_info['unit'].split()[0]}` (From {t_info['start_val']} to {t_info['end_val']})
                    ---
                    """)

            with t_col2:
                st.markdown("#### 📉 Head & Temperature Degradation Fits")
                if "ΔP Head (PSI)" in df_filtered and "Motor temp °C" in df_filtered:
                    trend_fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("ΔP Head Trend (PSI)", "Motor Temp Trend (°C)"))
                    
                    # ΔP scatter + trendline
                    trend_fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["ΔP Head (PSI)"], name="ΔP Head (PSI)", mode="lines", line=dict(color="#2196f3", width=1.0)), row=1, col=1)
                    if "ΔP Head (PSI)" in trends_data:
                        t_obj = trends_data["ΔP Head (PSI)"]
                        trend_fig.add_trace(go.Scatter(x=[df_filtered["Report_DateTime"].min(), df_filtered["Report_DateTime"].max()], y=[t_obj["start_val"], t_obj["end_val"]], name="Head Trend Line", line=dict(color="red", width=2.5, dash="dash")), row=1, col=1)

                    # Motor temp scatter + trendline
                    trend_fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Motor temp °C"], name="Motor Temp (°C)", mode="lines", line=dict(color="#f44336", width=1.0)), row=2, col=1)
                    if "Motor temp °C" in trends_data:
                        t_obj = trends_data["Motor temp °C"]
                        trend_fig.add_trace(go.Scatter(x=[df_filtered["Report_DateTime"].min(), df_filtered["Report_DateTime"].max()], y=[t_obj["start_val"], t_obj["end_val"]], name="Temp Trend Line", line=dict(color="yellow", width=2.5, dash="dash")), row=2, col=1)

                    trend_fig.update_layout(height=480, hovermode="x unified")
                    st.plotly_chart(trend_fig, use_container_width=True, key="fig_tab5_trend")

    # =============================================================
    # TAB 6: Events & Incidents Log (NEW)
    # =============================================================
    with tab6:
        st.subheader("⚡ Operational Events & Incidents Log")
        st.caption("Automatically detects discrete state transitions (Trips, Startups, Vibration Spikes, Pressure Drops).")

        events_list = detect_operational_events(df_filtered)
        if not events_list:
            st.success("✅ No abrupt trips, vibration surges, or shutdown incidents detected in the selected timeframe.")
        else:
            st.metric("Total Operational Events", f"{len(events_list)} Incidents Detected")

            # Events Plotly Timeline with Vertical Event Markers
            event_fig = go.Figure()
            if "VSD Amps/Load" in df_plot:
                event_fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["VSD Amps/Load"], name="Motor Current (A)", line=dict(color="#e91e63", width=1.5)))
            if "Vibration G's-Vx" in df_plot:
                event_fig.add_trace(go.Scatter(x=df_plot["Report_DateTime"], y=df_plot["Vibration G's-Vx"] * 200.0, name="Vibration (Scaled x200)", line=dict(color="#ff9800", width=1.2)))

            for ev in events_list[:30]: # Annotate up to top 30 events
                event_fig.add_vline(
                    x=ev["timestamp"],
                    line_width=1.5,
                    line_dash="dot",
                    line_color="red" if "Trip" in ev["event_type"] else ("orange" if "Vibration" in ev["event_type"] else "green")
                )

            event_fig.update_layout(
                title=f"Incident Event Markers on Timeline ({selected_well_id})",
                height=450,
                xaxis=dict(rangeslider=dict(visible=True), type="date"),
                hovermode="x unified"
            )
            st.plotly_chart(event_fig, use_container_width=True, key="fig_tab6_event")

            # Events Data Table
            st.markdown("#### 📜 Incident Log Table")
            events_df = pd.DataFrame(events_list)
            st.dataframe(events_df, use_container_width=True)

    # =============================================================
    # TAB 7: Fleet Fault Finder (Cross-Well Search) (NEW)
    # =============================================================
    with tab7:
        st.subheader("🌐 Fleet Fault Finder (Cross-Well Historical Search)")
        st.caption("Search across ALL 73 wells in the field to discover where and when a specific fault mode occurred.")

        if not HAS_MODELS:
            st.warning("Models package not found.")
        else:
            fault_options = list(FAULT_DEFINITIONS.keys())
            target_fault = st.selectbox("🔍 Select Target Fault Mode to Search across Fleet", fault_options, index=0)
            
            f_info = FAULT_DEFINITIONS.get(target_fault, {})
            st.info(f"**{target_fault}** ({f_info.get('severity', 'WARNING')}): {f_info.get('description', '')}")

            if st.button(f"🔎 Scan 73 Wells for '{target_fault}'", type="primary"):
                with st.spinner(f"Scanning historical data across all 73 wells for '{target_fault}'..."):
                    fleet_res = scan_fleet_for_fault_history(target_fault, max_wells=73)

                    if fleet_res.empty:
                        st.success(f"✅ Zero occurrences of '{target_fault}' found across the scanned wells.")
                    else:
                        st.markdown(f"### 🚩 Found {len(fleet_res)} Incidents of `{target_fault}` Across Fleet")

                        # Cluster & Well Summary
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.markdown("#### 🛢️ Incidents by Well")
                            well_counts = fleet_res["Well_ID"].value_counts().reset_index()
                            well_counts.columns = ["Well_ID", "Incident_Count"]
                            st.dataframe(well_counts, use_container_width=True)

                        with c2:
                            st.markdown("#### 📊 Fleet Distribution Chart")
                            bar_fig = px.bar(
                                well_counts,
                                x="Well_ID",
                                y="Incident_Count",
                                title=f"Historical '{target_fault}' Incidents per Well",
                                color="Incident_Count",
                                color_continuous_scale="Reds"
                            )
                            bar_fig.update_layout(height=350)
                            st.plotly_chart(bar_fig, use_container_width=True, key="fig_tab7_fleet_bar")

                        # Detailed Fleet Incident Table
                        st.markdown("#### 📋 Detailed Incident Log Across Fleet")
                        st.dataframe(fleet_res, use_container_width=True)

                        # Interactive Incident Forensic Deep-Dive
                        st.markdown("---")
                        st.subheader("🔬 Incident Forensic Deep-Dive & Tipping Evidence")
                        st.caption("Select any incident from the fleet log above to inspect its before-during-after tipping timeline, baseline corridor breakout, and physical evidence.")

                        incident_options = [
                            f"#{i+1} | Well: {r['Well_ID']} | Time: {str(r['Timestamp'])[:19]} | Health: {r['Health_Score']}/100"
                            for i, r in fleet_res.iterrows()
                        ]
                        sel_incident_str = st.selectbox(
                            "🎯 Select Incident to Inspect Forensic Tipping Pattern & Evidence:",
                            incident_options,
                            index=0
                        )
                        sel_idx = incident_options.index(sel_incident_str)
                        incident_meta = fleet_res.iloc[sel_idx].to_dict()

                        target_well = incident_meta["Well_ID"]
                        target_time = str(incident_meta["Timestamp"])

                        # Load the telemetry window around the incident
                        df_forensic = load_incident_telemetry_window(target_well, target_time, window_minutes=60)

                        # Get well profile from registry
                        well_prof = engine.registry.get_well_profile(target_well) if engine else {}

                        # 1. Summary Metric Chips
                        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                        m_c1.metric("Asset ID", target_well)
                        m_c2.metric("Detected Fault", incident_meta["Detected_Fault"])
                        m_c3.metric("Health Score at Trip", f"{incident_meta['Health_Score']:.1f} / 100")
                        m_c4.metric("Incident Timestamp", target_time[:19].replace("T", " "))

                        # Data Source Provenance Badge (§7 UI Transparency)
                        src_tag = "normalized.db (Historical Batch)"
                        if not df_forensic.empty and "Source_File" in df_forensic.columns:
                            first_src = str(df_forensic["Source_File"].iloc[0])
                            if "live" in first_src.lower() or "mqtt" in first_src.lower():
                                src_tag = "🟢 Live MQTT Stream (Edge Ingestion)"
                            else:
                                src_tag = f"🏛️ Historian Archive ({first_src})"
                        st.caption(f"📡 **Data Lineage:** `{src_tag}` | High-Resolution Window (±30m) | Loaded: `{len(df_forensic)} samples`")

                        # 2. Synchronized Tipping Timeline Plot
                        if render_incident_tipping_timeline is not None and not df_forensic.empty:
                            fig_tipping = render_incident_tipping_timeline(
                                df_forensic, incident_meta, well_prof, height=620
                            )
                            st.plotly_chart(fig_tipping, use_container_width=True, key=f"fig_tab7_tipping_{sel_idx}")
                        elif df_forensic.empty:
                            st.info(f"Detailed high-resolution telemetry window not found in normalized.db for Well {target_well} around {target_time}.")

                        # 3. Evidence Table & Recommended Advisory
                        e_col1, e_col2 = st.columns([3, 2])
                        with e_col1:
                            st.markdown("#### 📊 Parameter Breakout vs. Calibrated Normal Envelope (P10 - P90)")
                            if not df_forensic.empty and build_evidence_comparison_table is not None:
                                trip_row = df_forensic.iloc[len(df_forensic)//2].to_dict()
                                evidence_df = build_evidence_comparison_table(trip_row, well_prof)
                                st.dataframe(evidence_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("Parameter breakout table unavailable.")

                        with e_col2:
                            st.markdown("#### 🛠️ Recommended Engineering Advisory")
                            st.warning(f"**Immediate Action:** {incident_meta.get('Advisory', 'Inspect well parameters and verify choke/VFD status.')}")
                            st.markdown(f"""
                            **Diagnostic Summary:**
                            - **Fault Diagnosis:** `{incident_meta['Detected_Fault']}`
                            - **Detection Confidence:** `{float(incident_meta.get('Confidence', 0.95))*100:.1f}%`
                            - **Operational Status:** `{incident_meta.get('Status', 'CRITICAL')}`
                            - **Physical Mechanism:** Multi-parameter coupling diverged beyond the calibrated healthy envelope.
                            """)

    # =============================================================
    # TAB 8: Data Table Explorer & CSV Download
    # =============================================================
    with tab8:
        st.subheader("Filterable Data Explorer")
        st.caption("Inspect individual telemetry rows, filter columns, and export raw/normalized slices.")

        col_scope = st.radio(
            "📋 Select Columns to View",
            ["All Columns (Raw + Normalized + Physics)", "Raw Telemetry Only", "Normalized ML Features Only", "Physics Dynamics Only"],
            horizontal=True
        )

        if col_scope == "Raw Telemetry Only":
            display_cols = ["Report_DateTime"] + [c for c in STANDARD_SENSORS if c in df_filtered.columns] + (["VFD STS"] if "VFD STS" in df_filtered.columns else [])
            display_df = df_filtered[[c for c in display_cols if c in df_filtered.columns]]
        elif col_scope == "Normalized ML Features Only":
            display_cols = ["Report_DateTime"] + [c for c in df_filtered.columns if c.startswith("norm_")]
            display_df = df_filtered[[c for c in display_cols if c in df_filtered.columns]]
        elif col_scope == "Physics Dynamics Only":
            display_cols = ["Report_DateTime", "Delta_P_PSI", "Torque_Proxy_A_Hz", "Power_kVA", "Thermal_Elevation_C", "ΔP Head (PSI)", "Torque Proxy (A/Hz)", "Power Proxy (kVA)", "Thermal Elevation (°C)"]
            display_df = df_filtered[[c for c in display_cols if c in df_filtered.columns]]
        else:
            display_df = df_filtered

        st.dataframe(display_df, use_container_width=True, height=450)

        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Download Selected {col_scope} for {selected_well_id} (CSV)",
            data=csv_data,
            file_name=f"{selected_well_id}_{col_scope.replace(' ', '_').lower()}.csv",
            mime="text/csv",
            type="secondary"
        )


if __name__ == "__main__":
    main()
