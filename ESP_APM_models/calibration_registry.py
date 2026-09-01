"""
Well Calibration Registry Component
===================================
Manages parametric baseline envelopes (min, max, mean, std, median, p10, p90)
for all 73 individual wells across CCED field clusters (FS, FNW, FWS, ULFA),
with hierarchical family and global fallbacks.
"""

import os
import sys
import json
import glob
import re
import datetime
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

STANDARD_SENSORS = [
    "Inp bar/psi",
    "Int temp °C",
    "Motor temp °C",
    "Disch pr. Bar/psi",
    "Vibration G's-Vx",
    "Leak Current Ct",
    "Volt",
    "VSD Amps/Load",
    "Frequency",
    "DHG Current",
    "WHP (PSI)",
    "FLP (PSI)",
    "AP (PSI)"
]

def clean_col_key(col_name: str) -> str:
    """Standardizes incoming column strings to canonical sensor names."""
    if col_name is None:
        return ""
    s = str(col_name).strip()
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    s = s.replace("\xb0", "°").replace("\ufffdC", "°C").replace("C", "°C").replace("", "")
    s = re.sub(r'\s+', ' ', s).strip()

    c_low = s.lower()
    if "report" in c_low and "date" in c_low:
        return "Report_DateTime"
    if "file" in c_low and "date" in c_low:
        return "File_DateTime"
    if "well" in c_low:
        return "Wells"
    if "inp" in c_low or "intake" in c_low or "suction" in c_low:
        return "Inp bar/psi"
    if "int" in c_low and "temp" in c_low:
        return "Int temp °C"
    if "motor" in c_low and "temp" in c_low:
        return "Motor temp °C"
    if "disch" in c_low or "discharge" in c_low:
        return "Disch pr. Bar/psi"
    if "vib" in c_low:
        return "Vibration G's-Vx"
    if "leak" in c_low:
        return "Leak Current Ct"
    if "volt" in c_low:
        return "Volt"
    if "amp" in c_low or "load" in c_low:
        return "VSD Amps/Load"
    if "freq" in c_low or "hz" in c_low:
        return "Frequency"
    if "dhg" in c_low:
        return "DHG Current"
    if "whp" in c_low:
        return "WHP (PSI)"
    if "flp" in c_low:
        return "FLP (PSI)"
    if "ap" in c_low:
        return "AP (PSI)"
    if "vfd" in c_low or "sts" in c_low or "status" in c_low:
        return "VFD STS"
    if "cluster" in c_low:
        return "Cluster"
    return s


class WellCalibrationRegistry:
    """
    Scans categorized historical well datasets to construct baseline operating profiles.
    Caches baseline statistics in a local JSON registry for fast (<1ms) inference.
    """

    def __init__(
        self,
        categorized_dir: str = r"C:\Users\admin.DESKTOP-17T37DJ\Desktop\cced\categorized_wells",
        registry_file: Optional[str] = None
    ):
        self.categorized_dir = categorized_dir
        if registry_file is None:
            # Default to registry JSON in models folder or parent directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            registry_file = os.path.join(base_dir, "well_calibration_registry.json")
            if not os.path.exists(registry_file):
                parent_reg = os.path.join(os.path.dirname(base_dir), "well_calibration_registry.json")
                if os.path.exists(parent_reg):
                    registry_file = parent_reg

        self.registry_file = registry_file
        self.registry: Dict[str, Any] = {}
        self.family_profiles: Dict[str, Any] = {}
        self.global_profile: Dict[str, Any] = {}
        self._load_or_build()

    def _load_or_build(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.registry = data.get("wells", {})
                    self.family_profiles = data.get("families", {})
                    self.global_profile = data.get("global", {})
                if self.registry:
                    return
            except Exception as e:
                print(f"[!] Warning loading registry {self.registry_file}: {e}. Rebuilding...")

        self.build_registry_from_files()

    def build_registry_from_files(self):
        print("Building well calibration baseline registry from categorized files...")
        csv_files = glob.glob(os.path.join(self.categorized_dir, "**", "*.csv"), recursive=True)
        csv_files = [f for f in csv_files if "Wells_Summary_Index" not in f]

        if not csv_files:
            print(f"[!] Warning: No categorized well CSVs found in {self.categorized_dir}.")
            return

        all_well_stats = {}
        family_accumulators = {}
        all_dfs = []

        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path, low_memory=False)
                df.columns = [clean_col_key(c) for c in df.columns]
                df = df.loc[:, ~df.columns.duplicated()].copy()
                
                well_name = os.path.splitext(os.path.basename(csv_path))[0].replace("_", "-")
                if "Wells" in df.columns and len(df["Wells"].dropna()) > 0:
                    well_name = str(df["Wells"].dropna().iloc[0]).strip()
                
                family = re.match(r'^([A-Za-z]+)', well_name).group(1).upper() if re.match(r'^([A-Za-z]+)', well_name) else "OTHER"
                
                well_stats = {"family": family, "sensors": {}}
                for sensor in STANDARD_SENSORS:
                    if sensor in df.columns:
                        s_vals = pd.to_numeric(df[sensor], errors="coerce").dropna()
                        pos_vals = s_vals[s_vals > 0]
                        act_vals = pos_vals if len(pos_vals) > 0 else s_vals
                        if len(s_vals) > 0:
                            well_stats["sensors"][sensor] = {
                                "min": float(s_vals.min()),
                                "max": float(s_vals.max()),
                                "mean": float(act_vals.mean()),
                                "std": float(act_vals.std()) if len(act_vals) > 1 else 1.0,
                                "median": float(act_vals.median()),
                                "p10": float(np.percentile(act_vals, 10)),
                                "p90": float(np.percentile(act_vals, 90))
                            }
                
                all_well_stats[well_name] = well_stats
                
                if family not in family_accumulators:
                    family_accumulators[family] = []
                family_accumulators[family].append(df)
                all_dfs.append(df)
            except Exception as e:
                print(f"  [!] Error profiling {csv_path}: {e}")

        self.registry = all_well_stats

        # Compute Family profiles
        for fam, dfs in family_accumulators.items():
            fam_df = pd.concat(dfs, ignore_index=True)
            self.family_profiles[fam] = self._compute_df_profile(fam_df)

        # Compute Global profile
        if all_dfs:
            master_df = pd.concat(all_dfs, ignore_index=True)
            self.global_profile = self._compute_df_profile(master_df)

        # Save to JSON
        cache_data = {
            "wells": self.registry,
            "families": self.family_profiles,
            "global": self.global_profile,
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        print(f"[OK] Calibration Registry built for {len(self.registry)} wells and saved to {self.registry_file}")

    def _compute_df_profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        profile = {"sensors": {}}
        for sensor in STANDARD_SENSORS:
            if sensor in df.columns:
                s_vals = pd.to_numeric(df[sensor], errors="coerce").dropna()
                pos_vals = s_vals[s_vals > 0]
                act_vals = pos_vals if len(pos_vals) > 0 else s_vals
                if len(s_vals) > 0:
                    profile["sensors"][sensor] = {
                        "min": float(s_vals.min()),
                        "max": float(s_vals.max()),
                        "mean": float(act_vals.mean()),
                        "std": float(act_vals.std()) if len(act_vals) > 1 else 1.0,
                        "median": float(act_vals.median()),
                        "p10": float(np.percentile(act_vals, 10)),
                        "p90": float(np.percentile(act_vals, 90))
                    }
        return profile

    def get_well_profile(self, well_id: str) -> Dict[str, Any]:
        """Returns baseline profile for specific well, with fallback to family/global."""
        if well_id in self.registry:
            return self.registry[well_id]
        
        # Family fallback
        m = re.match(r'^([A-Za-z]+)', str(well_id).strip())
        fam = m.group(1).upper() if m else "OTHER"
        if fam in self.family_profiles:
            return {"family": fam, "sensors": self.family_profiles[fam].get("sensors", {})}
        
        return {"family": "GLOBAL", "sensors": self.global_profile.get("sensors", {})}
