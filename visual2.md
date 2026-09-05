# Visual 2: Subsystem Health Equalizer & Well Pressure Profile
### *(Physical Space & Subsystem Balance Localization)*

> **Document Purpose:** Complete technical explainer, operational guide, and mathematical foundation for **Visual 2 (Subsystem Health Equalizer & Well Pressure Profile)**. Explains what it is in simple words, why the old 2D phase plane was canceled in favor of intuitive balance bars and physical wellbore gradients, how an operator reads it in 3 seconds, and presents real ground-truth data from `cced_esp/data/labelled.db` (Well `FSWS-003`).

---

## 1. What Is This Visual in Simple Words?

### In One Sentence:
**Visual 2 answers "WHERE did the problem happen?": it shows which subsystem broke (Hydraulic, Electrical, Thermal, or Mechanical) via intuitive audio-equalizer balance bars, and plots the well's physical pressure gradient from reservoir to wellhead to pinpoint where pressure was lost.**

---

### Why the 2D Bivariate Phase Plane Was Canceled:
* **The Canceled Approach:** Earlier designs tested a 2D Bivariate Phase Plane ($I_{\text{motor}}$ vs. $P_{\text{intake}}$) across 4 quadrants. While mathematically sound, operators found it abstract, unintuitive, and difficult to read in fast-paced control room environments.
* **The Production Solution:** Visual 2 was replaced with two clear, physical representations:
  1. **The 4-Subsystem Health Equalizer (Default / Universal):** Like a stereo graphic equalizer, it displays 4 horizontal balance bars. Green means healthy baseline; red bars deviating left or right show exactly which subsystem is in trouble.
  2. **The Wellbore Pressure Depth Profile (Adaptive for Hydraulic Faults):** When downhole and surface pressure sensors ($PIP$, $PDP$, $WHP$) are available, it displays a vertical line from surface ($0\text{ ft}$) to reservoir ($7,520\text{ ft}$), revealing that the pump stage is delivering $\Delta P = 0\text{ psi}$.

---

## 2. Layout A: The 4-Subsystem Health Equalizer

### The Concept:
Every ESP operates across 4 physical subsystems. Instead of drowning operators in 14 raw numbers, the Equalizer aggregates them into 4 clear balance meters:

```
====================================================================================================
 🎛️ VISUAL 2: SUBSYSTEM HEALTH EQUALIZER | WELL: FSWS-003 | STATUS: CRITICAL TRIP
====================================================================================================
 Baseline Regime: 42–48 Hz | Telemetry Time: 2026-03-12 14:15:00Z | Health Index: 28 / 100
 
 1. HYDRAULICS [PIP, PDP, WHP]
    [-52.0%] ◄██████████████████████│                  │ [+0.0%] [CRITICAL DROP]
             Intake 198 PSI (-42%) | Discharge 764 PSI (-58%) | Head Collapsed
 
 2. ELECTRICAL [Amps, Volt, Freq]
    [-31.2%] ◄██████████│                              │ [+0.0%] [UNDERLOAD TRIP]
             Current 37.3 A (-31%) | Voltage 293 V (Nominal) | Freq 44 Hz Steady
 
 3. THERMAL    [Motor Temp, Intake Temp]
             │                  │████►                   [+10.4%] [WARNING RISE]
             Motor Temp 79.5°C (+10%) | Cooling Flow Deficit
 
 4. MECHANICAL [Vibration Vx, Torque Proxy]
             │                  │██████████►             [+44.4%] [WARNING SURGE]
             Vibration 0.13 G (+44%) | Vapor Bubble Collapse / Slugging
 ---------------------------------------------------------------------------------------------------
 💡 DIFFERENTIAL DIAGNOSIS (RULING OUT):
 Closest Match: GAS LOCK UNDERLOAD (0.91 Cosine Similarity)
 Ruled Out:     SAND INGESTION (0.14) & FLUID EMULSION (0.08)
 Key Proof:     Motor current collapsed (-31%). Sand and emulsion cause heavy overload current (+60%).
====================================================================================================
```

### How to Read the Equalizer in 3 Seconds:
* **Center White Line:** Normal operating baseline for this well at its current VFD speed regime (from `regime_baseline_registry.json`).
* **Green Shaded Center Box ($\pm 15\%$):** Safe operating corridor.
* **Red / Blue Deviations:** 
  * Bars extending **Left** indicate collapse/underload (e.g., loss of pressure or motor load).
  * Bars extending **Right** indicate overload/spikes (e.g., overheating or vibration).
* **The Auto-Generated Diagnosis:** The text at the bottom compares the 4-bar shape against `fault_signature_library.json` using cosine similarity, explicitly proving which fault occurred and which faults were ruled out.

---

## 3. Layout B: The Wellbore Pressure Depth Profile

### The Physical Digital Twin (Confirmed by Field Lead Demo):
When an incident is classified as a Hydraulic fault and downhole sensors are present, Visual 2 can display the **Vertical Depth vs. Pressure Profile** (matching `media_1788607948984.png`):

```
 Depth (ft)
   0 ft ──► ● Wellhead (WHP) = 85 psi
            │ \
            │  \   [Tubing Fluid Column Gradient]
            │   \
 2,000  ──► │    \
            │     \
 4,000  ──► │      \
            │       \
 6,000  ──► │        ● Pump Discharge (PDP) = 1,240 psi  ┐
            │        │                                    ├─► PUMP ΔP = 0 PSI (140 STAGES)
            │        ● Pump Intake (PIP)    = 1,240 psi  ┘
            │       /
 7,000  ──► │      ● Flowing Bottomhole (Pwf) = 1,752 psi
            │     /
 7,520  ──► └─── ● Reservoir (Pr) = 2,737 psi
            0       500     1,000    1,500    2,000    2,500    3,000  Pressure (psi)
```

### What It Tells the Operator:
* **The Smoking Gun:** Intake pressure is $1,240\text{ psi}$ and discharge pressure is $1,240\text{ psi}$.
* The 140 pump stages are generating **zero differential pressure boost ($\Delta P = 0\text{ psi}$)**.
* Fluid entered the pump and exited the pump at the exact same pressure. The pump is totally air-locked or spinning freely.

---

## 4. Ground-Truth Data Verification: Well `FSWS-003`

From `cced_esp/data/labelled.db`, here is the telemetry snapshot for the Gas Lock Underload incident:

| Subsystem | Sensor Parameter | Baseline (Regime 42–48 Hz) | Event Telemetry | Deviation % | Subsystem Health Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Hydraulic** | Intake Pressure ($PIP$) | $345.0\text{ psi}$ | $198.5\text{ psi}$ | $-42.5\%$ | 🚨 **CRITICAL COLLAPSE** |
| **Hydraulic** | Discharge Pressure ($PDP$) | $1,820.0\text{ psi}$ | $764.0\text{ psi}$ | $-58.0\%$ | 🚨 **CRITICAL COLLAPSE** |
| **Electrical** | Motor Amps ($I_{\text{motor}}$) | $54.2\text{ A}$ | $37.3\text{ A}$ | $-31.2\%$ | 🚨 **UNDERLOAD TRIP** |
| **Electrical** | Line Voltage ($V$) | $294.5\text{ V}$ | $293.0\text{ V}$ | $-0.5\%$ | ✅ **NOMINAL** |
| **Thermal** | Motor Temp ($T_{\text{motor}}$) | $72.0^\circ\text{C}$ | $79.5^\circ\text{C}$ | $+10.4\%$ | ⚠️ **COOLING DEFICIT** |
| **Mechanical** | Radial Vibration ($V_x$) | $0.09\text{ G}$ | $0.13\text{ G}$ | $+44.4\%$ | ⚠️ **GAS SLUGGING SURGE** |

---

## 5. Mathematical Foundation (Differential Diagnosis)

The auto-generated caption below Visual 2 is computed via **Cosine Similarity** between the live subsystem deviation vector $\vec{\delta}_{\text{live}}$ and all canonical vectors $\vec{S}_k$ in `fault_signature_library.json`:

$$\text{Similarity}(\vec{\delta}_{\text{live}}, \vec{S}_k) = \frac{\sum_{i=1}^4 \delta_{\text{live}, i} \cdot S_{k, i}}{\sqrt{\sum_{i=1}^4 \delta_{\text{live}, i}^2} \sqrt{\sum_{i=1}^4 S_{k, i}^2}}$$

### Computed Results for `FSWS-003`:
1. $\text{Sim}(\text{Gas Lock Underload}) = \mathbf{0.91}$ $\rightarrow$ **Top Match**
2. $\text{Sim}(\text{Pump-Off / Starvation}) = 0.74$ $\rightarrow$ Secondary Consideration
3. $\text{Sim}(\text{Sand Ingestion Jam}) = 0.14$ $\rightarrow$ **Ruled Out**
4. $\text{Sim}(\text{Fluid Emulsion}) = 0.08$ $\rightarrow$ **Ruled Out**

---

## 6. Role in the 4-Visual Diagnostic Flow

* **Visual 1 (Timeline):** *When* did the well start degrading? (Tipping point at 14:15).
* **Visual 2 (Equalizer & Depth Profile):** *Where* did it fail? (**Hydraulics & Pump Stage $\Delta P = 0\text{ psi}$**).
* **Visual 3 (Pump Curve):** *Is* the pump hardware destroyed? (Operating point at 0 flow, curve intact).
* **Visual 4 (SHAP & Playbook):** *Why* did it happen & *What* do we do? (Gas Lock confirmed, drop Hz by 4, vent casing head).
