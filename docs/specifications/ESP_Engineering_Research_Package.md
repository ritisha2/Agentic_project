# ESP Engineering Calculation Service — Research Package
**Purpose:** Authoritative engineering-data foundation for a deterministic ESP Engineering Calculation Service. The LLM is NOT the calculation authority — this package defines what a deterministic engine must implement, and flags everything that cannot yet be verified.
**Compiled:** 2026 (standards status verified via web search on this date; verify again before production freeze — standards get reaffirmed, revised, or withdrawn)

> **Governing rule applied throughout:** No formula, correction factor, limit, or constant is asserted unless it is either (a) fundamental physics/mathematics, (b) explicitly sourced to a named standard/edition, or (c) explicitly marked **REQUIRES ENGINEERING VALIDATION**. Where I could not independently confirm exact section/table/figure numbers from the primary document (most standards are paywalled and not full-text searchable), I say so instead of guessing.

---

## 1. Authoritative Reference Registry (verified 2026)

### 1.1 API Recommended Practices — ESP-specific (API 11S series)

| Doc # | Title | Edition/Status (verified 2026) | Scope | Applies to |
|---|---|---|---|---|
| **API RP 11S** | Operation, Maintenance and Troubleshooting of Electric Submersible Pump Installations | 3rd Ed.; earlier edition reaffirmed 2013 — **verify current reaffirmation/edition status directly with API before production use**, exact current publication date not independently confirmed | ESP system components, operation, maintenance, troubleshooting for tubing-deployed installations. **Explicitly not intended for equipment selection/application.** | Troubleshooting logic, operating limits guidance |
| **API RP 11S1** | Electrical Submersible Pump Teardown Report | Recommended teardown report form + generic equipment schematics | Standard teardown/failure documentation format | Reliability/failure classification (Section G) |
| **API RP 11S2** | Electric Submersible Pump Testing | Guidelines/procedures for ESP performance testing for product consistency | Pump performance test methodology | Pump performance curve provenance/validation |
| **API RP 11S3** | Electrical Submersible Pump Installations | 2nd Ed., March 1999, reaffirmed October 2013 | Installation/replacement of ESP system components on tubing | Installation-condition validity checks |
| **API RP 11S4** | Sizing and Selection of Electric Submersible Pump Installations | 3rd Ed., July 2002, reaffirmed October 2013 — **WITHDRAWN** (confirmed via standards distributor records, 2026) | Component sizing/selection methodology; discusses PVT correlations, multiphase flow correlations, IPR use | **Withdrawn — cannot be cited as current authority.** Any sizing/selection formulas historically drawn from 11S4 must be re-sourced (ISO 15551 informative annexes, OEM design manuals, or peer-reviewed literature) and explicitly flagged if no current standard covers them. |
| **API RP 11S6** | Testing of Electric Submersible Pump Cable Systems | Establishes recommendations for 3-conductor ESP power cable testing | Cable system testing (not calculation-relevant directly; supports cable-related input validation) |
| **API RP 11S8** | Electric Submersible System Vibrations | Guidelines for consistency in ESP system vibration control/analysis; covers vibration limits, testing, analysis | **Vibration calculations and limit-checking (Section E/F)** |
| API RP 11R | Electric Submersible Pump Installations (2nd Ed.) | Referenced by GlobalSpec catalog; content/current status not independently verified beyond title | Historical/legacy — **REQUIRES ENGINEERING VALIDATION** before use; may be superseded by 11S-series and ISO 15551 |

**Action required before implementation:** API document numbers, editions, and reaffirmation dates above were captured from third-party standards distributors (GlobalSpec, Accuristech, production-technology.org), not from api.org directly, because API's own catalog was not reachable in this research pass. **Every edition/date/status in this table must be re-verified directly against the API Publications Store before being hard-coded as a compliance reference in the production system.**

### 1.2 ISO Standards

| Doc # | Title | Edition | Status | Scope | Notes |
|---|---|---|---|---|---|
| **ISO 15551:2023** | Petroleum and natural gas industries — Drilling and production equipment — Electric submersible pump systems for artificial lift | Edition 1, published 2023-09 | **Current — supersedes ISO 15551-1:2015** | Design, design verification/validation, manufacturing, performance ratings, functional evaluations, handling/storage of tubing-deployed ESP systems (pump, gas handling devices, discharge heads, seal chambers, intake systems, gas separators, induction motors, couplings, MLE, pothead, power cables) | **Contains informative annexes directly relevant to this service**, including: guidance for establishing the **Recommended Operating Range (ROR)** of an ESP system, functional-evaluation guidelines, considerations for 3-phase VSD use, post-run analysis, downhole monitoring, and permanent-magnet motor information. This is the single most important current standard for ROR/operating-envelope logic (Section E). |
| ISO 15551-1:2015 | (superseded part) | Edition withdrawn/superseded by ISO 15551:2023 | Superseded | Same general scope as above, prior edition | Do not use as current authority; retained here only because legacy client documents may still reference it. |

**Action required:** ISO full text (including the ROR annex) was not retrievable in this pass (ISO documents are paywalled). The exact ROR calculation method, tolerance bands, and any numeric correction factors in ISO 15551:2023's informative annexes **must be pulled from the purchased standard text directly** — I have identified *that* this content exists and *where* (informative annexes of ISO 15551:2023), but I have not verified the numeric content itself, so no ROR formula from this standard is reproduced below. Mark ROR determination as **REQUIRES ENGINEERING VALIDATION** until the annex text is sourced.

### 1.3 Hydraulic Institute (ANSI/HI) Standards — general centrifugal pump engineering

| Doc # | Title | Edition | Status | Scope | Applies to |
|---|---|---|---|---|---|
| **ANSI/HI 9.6.7-2021** | Rotodynamic Pumps — Guideline for Effects of Liquid Viscosity on Performance | 2021 (supersedes 2015, 2010 editions) | Current | Empirical method for correcting rotodynamic pump performance (Q, H, η, power) from water-test curves to viscous-liquid performance. Applicable to Newtonian liquids; the 2015 edition's stated range was radial-flow OH/BB/VS pumps, kinematic viscosity roughly 1–4000 cSt — **confirm this range still applies verbatim in the 2021 edition before hard-coding a validity boundary.** | **Viscosity correction (Section D)** — the correction-factor charts/curves (CQ, CH, Cη) in this standard are the authoritative source. They must be digitized from the actual standard (or an OEM-licensed digital implementation of it), not approximated from memory. |
| ANSI/HI 9.6.6 | Rotodynamic Pumps for Pump Piping | Referenced/current per HI catalog | Piping-side effects on pump performance (inlet/outlet piping) | Secondary; relevant only if surface/near-wellhead piping effects are modeled — likely out of scope for a downhole ESP calc service |
| ANSI/HI 1.3 (general series) | Rotodynamic Centrifugal Pumps — Design and Application | Referenced in HI catalog | Not independently verified in this pass — general nomenclature/affinity-law reference used industry-wide | Affinity-law terminology cross-check only. **The affinity-law formulas themselves (Section A) are standard fluid-mechanics relations, not unique IP of HI 1.3** — cite HI 1.3 as a convenience reference, not as the sole source of the physics. |

### 1.4 Fundamental physics / non-standard-specific relations

Some ESP calculations (hydrostatic head↔pressure conversion, hydraulic power, affinity laws) are **general fluid-mechanics/thermodynamics relations**, not proprietary content of any single standard. They are treated in Section 2 as **Standard-derived (physics)** rather than attributed to a specific document number, per the "do not invent a standard reference" rule — I will not force-fit a fabricated citation onto textbook physics. Where a standard *does* independently publish the same relation (e.g., HI general references), that is noted as a convenience cross-reference, not as the origin of the physics.

### 1.5 Standards NOT verified in this pass — explicitly flagged

The following are commonly cited in ESP engineering practice but were **not independently verified** in this research pass and must not be hard-coded until confirmed:
- IEEE 1019 (ESP cable insulation) — appeared as a cross-reference in API 11S6/11S3 search results; scope not independently confirmed beyond title.
- NEMA MG-1 (motor design/performance, if used for ESP motor thermal/electrical limits) — **not searched; REQUIRES ENGINEERING VALIDATION.**
- API STD 610 / ISO 13709 (general centrifugal pumps, petroleum industry) — surface-pump standard; applicability to downhole ESP calculations is doubtful and **REQUIRES ENGINEERING VALIDATION** if invoked.
- Any specific PVT correlations (Standing, Vasquez-Beggs, Beggs-Brill, Turpin gas-handling correlation, etc.) — these are peer-reviewed literature, not standards. Priority tier 6 (peer-reviewed literature) applies; the *choice* of correlation is a client/engineering decision, not something this package should presume. **Marked REQUIRES ENGINEERING VALIDATION / CLIENT SELECTION throughout Section D.**
- OEM-specific design manuals (Baker Hughes/Centrilift, SLB/Reda, Weatherford) — proprietary, asset-specific, cannot be sourced generically. See Section B.

---

## 2. Calculation Definitions

Structure per calculation: ID, Name, Purpose, Domain, Formula, Required/Optional inputs, Units, Unit conversions, Validity conditions, Operating range, Assumptions, Output, Uncertainty, Reference, Section/Table/Figure, OEM dependency, Asset dependency, Failure condition.

### SECTION A — Standard-derived calculations (physics-based, universal within stated limits)

---
**CALCULATION ID:** `A1_HEAD_PRESSURE_CONVERSION`
**Name:** Pressure–Head Conversion
**Purpose:** Convert differential pressure to equivalent fluid head (or vice versa) for pump curve comparison (pump curves are published in ft of head; field data is usually psi).
**Domain:** Fluid statics
**Formula:** `H_ft = (ΔP_psi × 2.31) / SG`  and inverse `ΔP_psi = (H_ft × SG) / 2.31`
(2.31 = 144 in²/ft² ÷ 62.4 lb/ft³, the specific weight of fresh water at standard conditions — a dimensional-conversion constant, not a fitted engineering coefficient)
**Required inputs:** ΔP (psi), fluid specific gravity (SG) at flowing conditions
**Optional inputs:** none
**Units:** psi, ft, dimensionless SG
**Unit conversions:** none beyond the formula itself
**Input validity conditions:** SG > 0; ΔP finite and from a single consistent measurement window
**Operating range:** Valid for incompressible single-phase liquid; not valid for two-phase (gassy) columns without a gas-adjusted mixture SG — see D4/D2.
**Assumptions:** Fluid is treated as a single-phase liquid with the stated SG; no compressibility correction.
**Output:** `head_ft` or `pressure_psi`
**Uncertainty:** Directly propagates SG uncertainty; if SG is itself derived from a blended/gassy stream, propagate that uncertainty forward.
**Reference standard/document:** Fundamental fluid statics (no proprietary standard; universally used oilfield conversion constant). Not attributed to API/ISO/HI.
**Exact section/table/figure:** N/A (textbook relation)
**OEM dependency:** None
**Asset-specific dependency:** SG must be the asset's actual flowing-condition fluid property (see PVT table), not a generic default.
**Failure condition if required input missing:** If SG unavailable, calculation must fail closed (no default SG substitution) — flag `"REQUIRES ENGINEERING VALIDATION: missing fluid SG"`.

---
**CALCULATION ID:** `A2_HYDRAULIC_POWER`
**Name:** Hydraulic (Water) Horsepower
**Purpose:** Compute the hydraulic power delivered to the fluid, a required intermediate for efficiency and BHP calculations.
**Domain:** Pump hydraulics
**Formula:** `WHP = (Q_bpd × H_ft × SG) / 135,000`
(135,000 is the standard oilfield unit-conversion constant for bbl/day, ft, hp — derived from 5.615 ft³/bbl, 62.4 lb/ft³ water density, 1 day = 1440 min, and 33,000 ft·lb/min per hp; it is a dimensional-conversion product, not an empirical fit)
**Required inputs:** Flow rate Q (bpd), total dynamic head H (ft), fluid SG at pump conditions
**Optional inputs:** none
**Units:** bpd, ft, hp
**Unit conversions:** If Q is given in bbl/day it must not be confused with bbl/day at standard conditions vs. flowing conditions — flowing-condition volume must be used (accounts for formation volume factor / free gas if present; see D2).
**Input validity conditions:** Q ≥ 0; H ≥ 0; SG > 0
**Operating range:** Single-phase liquid assumption; for gassy fluid, Q and SG must already reflect flowing (in-situ) mixture conditions per D2/D4, or the result understates true power requirement.
**Assumptions:** No slippage/recirculation losses included — this is ideal hydraulic power, not shaft power.
**Output:** `whp_hp`
**Uncertainty:** Propagates from Q, H, SG measurement uncertainty.
**Reference standard/document:** Fundamental fluid mechanics / standard oilfield engineering conversion (constant is universally used in industry references, e.g., pump handbooks); not a unique claim of any single current API/ISO/HI standard.
**Exact section/table/figure:** N/A
**OEM dependency:** None for the formula; H must come from a valid operating point (see C1).
**Asset-specific dependency:** Q, H, SG are all asset/well-specific measured or derived values.
**Failure condition:** Missing any of Q, H, SG → fail closed, no substitution.

---
**CALCULATION ID:** `A3_BRAKE_HORSEPOWER`
**Name:** Pump Brake Horsepower (Shaft Power)
**Purpose:** Determine actual shaft power required, accounting for pump hydraulic efficiency.
**Domain:** Pump hydraulics
**Formula:** `BHP = WHP / η_pump`
**Required inputs:** WHP (from A2), pump hydraulic efficiency η_pump at the operating point
**Optional inputs:** none
**Units:** hp, dimensionless (0 < η ≤ 1)
**Unit conversions:** none
**Input validity conditions:** 0 < η_pump ≤ 1 (values outside this range indicate bad curve data — must fail, not clamp silently)
**Operating range:** η_pump must be read from a valid OEM performance curve at the actual operating flow rate (see B1) — not assumed constant across the curve.
**Assumptions:** Mechanical losses beyond hydraulic efficiency (bearing/seal drag) are typically embedded in the OEM-published curve; do not double-count unless the OEM curve explicitly separates them.
**Output:** `bhp_per_stage` or `bhp_total` (stage count multiplier is OEM/asset data — see B1/E)
**Uncertainty:** η_pump curve uncertainty (OEM test tolerance) propagates directly and often dominates.
**Reference standard/document:** Standard pump-hydraulics relation (fundamental). η_pump sourcing governed by API RP 11S2 (ESP performance testing methodology) for how OEM curves should have been generated, and ANSI/HI 9.6.7 if viscosity-corrected.
**Exact section/table/figure:** N/A for the formula itself; API RP 11S2 exact section not confirmed in this pass — **REQUIRES ENGINEERING VALIDATION** to cite a section number.
**OEM dependency:** HIGH — η_pump at the operating point comes entirely from the OEM curve for that specific pump model/stage.
**Asset-specific dependency:** Actual flow rate and stage count.
**Failure condition:** No valid η_pump at operating Q → fail closed; do not interpolate/extrapolate beyond the OEM curve's published range without flagging `"REQUIRES ENGINEERING VALIDATION: operating point outside published curve range"`.

---
**CALCULATION ID:** `A4_AFFINITY_LAWS_SPEED_CORRECTION`
**Name:** Affinity-Law Frequency/Speed Correction
**Purpose:** Scale pump performance (Q, H, BHP) from a reference frequency/speed to an operating frequency/speed (e.g., 60 Hz base curve to VSD operating frequency).
**Domain:** Pump hydraulics — similarity laws
**Formula:**
`Q2 = Q1 × (N2/N1)`
`H2 = H1 × (N2/N1)²`
`BHP2 = BHP1 × (N2/N1)³`
where N = rotational speed (proportional to drive frequency for a fixed-slip induction motor, subject to motor slip correction — see C2/OEM motor data)
**Required inputs:** Reference-condition Q1, H1, BHP1 (from OEM base curve, typically 60 Hz); N1 (base frequency/speed); N2 (target frequency/speed)
**Optional inputs:** Motor slip correction (OEM motor data) if converting frequency→actual shaft speed rather than using frequency ratio directly
**Units:** bpd, ft, hp, Hz or RPM (consistent ratio — units cancel)
**Unit conversions:** N1, N2 must be in the same unit (both Hz or both RPM)
**Input validity conditions:** N2/N1 ratio should remain within the range validated by the OEM/standard for affinity-law applicability — large speed ratios (well outside ~50–100% of design speed) invalidate the simple cube/square law due to Reynolds-number and geometry effects.
**Operating range:** Affinity laws assume geometrically similar operation on the *same* system curve region; they do **not** by themselves relocate the BEP on a dimensional (Q,H) plot in a way that guarantees the new operating point is still within the pump's safe operating envelope — that check is separate (see E1, ROR).
**Assumptions:** Constant efficiency across the affinity-law transformation (η2 ≈ η1) — this is a standard simplifying assumption but is itself an approximation; large frequency excursions require OEM-verified efficiency at the new speed, not an assumed constant.
**Output:** `Q2_bpd`, `H2_ft`, `BHP2_hp`
**Uncertainty:** Error grows with |N2/N1 − 1|; the constant-efficiency assumption is the dominant error source at large speed changes.
**Reference standard/document:** Standard centrifugal-pump similarity laws (fundamental fluid mechanics), conventionally documented in Hydraulic Institute general references (ANSI/HI 1.3 series) and virtually every pump-hydraulics textbook. Exact HI section not confirmed in this pass.
**Exact section/table/figure:** REQUIRES ENGINEERING VALIDATION (need direct HI 1.3 text access)
**OEM dependency:** Base curve (Q1,H1,BHP1) is OEM data at N1.
**Asset-specific dependency:** N2 is the actual VSD operating frequency for that well.
**Failure condition:** Missing N1 (assumed base frequency without confirmation) → fail closed; do not assume 60 Hz silently — some fleets run 50 Hz base curves.

---
**CALCULATION ID:** `A5_BEP_PERCENT_OF_RATE`
**Name:** Percent of Best Efficiency Point (BEP)
**Purpose:** Express current operating rate as a percentage of the pump's BEP rate — a standard health/efficiency screening metric.
**Domain:** Pump hydraulics
**Formula:** `%BEP = (Q_actual / Q_BEP) × 100`
**Required inputs:** Q_actual (operating point, from C1), Q_BEP (from OEM curve, at actual operating frequency — apply A4 if curve is at a different base frequency)
**Optional inputs:** none
**Units:** bpd, %
**Unit conversions:** none
**Input validity conditions:** Q_BEP must be frequency-matched to Q_actual's operating frequency (via A4), not read off a mismatched base-frequency curve.
**Operating range:** N/A (this is a ratio metric, not itself range-limited)
**Assumptions:** Q_BEP shift with frequency follows the affinity law (A4) — same caveats apply.
**Output:** `pct_bep`
**Uncertainty:** Inherits OEM curve uncertainty plus affinity-law approximation if frequency-shifted.
**Reference standard/document:** Standard pump-engineering metric; recommended/acceptable %BEP operating bands are typically **client-approved or OEM-recommended**, not fixed by API/ISO — do not hard-code a "70–120% of BEP is acceptable" type band without a cited client standard or OEM spec (see Section E).
**Exact section/table/figure:** N/A for the ratio formula; acceptable-band source is E-category.
**OEM dependency:** Q_BEP location.
**Asset-specific dependency:** Q_actual.
**Failure condition:** No OEM Q_BEP available at the correct frequency → fail closed.

---

### SECTION B — OEM-data-dependent calculations (cannot be standardized generically)

---
**CALCULATION ID:** `B1_PUMP_CURVE_LOOKUP`
**Name:** Pump Performance Curve Interpolation (H, η, BHP vs. Q)
**Purpose:** Retrieve head, efficiency, and power at a given flow rate from the OEM-published (or OEM-tested per API RP 11S2 methodology) performance curve for the specific pump model/series/stage design.
**Domain:** OEM pump hydraulics
**Formula:** No universal formula — interpolation (typically piecewise-polynomial or spline) over digitized OEM curve data points, specific to pump model, stage type, and base test frequency.
**Required inputs:** Pump model/series ID, number of stages, base test frequency, digitized curve data (Q,H,η,BHP tuples), target Q
**Optional inputs:** Curve revision/test date, impeller trim (if trimmed impellers are used)
**Units:** bpd, ft (per stage or total), %, hp (per stage or total)
**Unit conversions:** Per-stage vs. total-stack values must be tracked consistently — a frequent source of calculation error.
**Input validity conditions:** Target Q must fall within the OEM-published curve range; extrapolation beyond published range is invalid without OEM confirmation.
**Operating range:** OEM-published minimum/maximum recommended flow (often tied to the ROR concept in ISO 15551:2023 informative annex).
**Assumptions:** Curve is for new, undamaged equipment at rated conditions unless a degradation/wear correction is separately applied (not covered by any standard identified in this pass — **REQUIRES ENGINEERING VALIDATION** if wear-derating is needed).
**Output:** `H_ft`, `eta_pct`, `bhp_per_stage` at target Q
**Uncertainty:** OEM test tolerance per API RP 11S2 testing methodology (exact tolerance bands not confirmed in this pass — REQUIRES ENGINEERING VALIDATION).
**Reference standard/document:** OEM published curve, generated per API RP 11S2 test methodology (if OEM followed it — not guaranteed for all vendors/eras of equipment).
**Exact section/table/figure:** N/A — proprietary OEM document, not a public standard.
**OEM dependency:** COMPLETE — this calculation cannot exist without the specific OEM curve dataset.
**Asset-specific dependency:** Which pump model/stage count is actually installed in that well (asset equipment record).
**Failure condition:** No matching OEM curve for the installed pump model → fail closed, flag `"REQUIRES OEM DATA: no curve on file for model {X}"`. Never substitute a "similar" pump's curve without an explicit, logged engineering override.

---
**CALCULATION ID:** `B2_MOTOR_PERFORMANCE_LOOKUP`
**Name:** Motor Performance Curve / Nameplate Lookup
**Purpose:** Retrieve motor amps, power factor, efficiency, and temperature rise vs. load from OEM motor data.
**Domain:** OEM electrical
**Formula:** No universal formula — OEM motor curve/nameplate lookup.
**Required inputs:** Motor model, nameplate rated voltage/current/hp/frequency, OEM performance curve (if available beyond nameplate)
**Optional inputs:** Ambient/downhole temperature derating curve
**Units:** V, A, hp, Hz, °F/°C
**Unit conversions:** Volts must be matched to actual configuration (series/parallel motor sections if tandem).
**Input validity conditions:** Nameplate data must match the physically installed motor serial/model — not a catalog default.
**Operating range:** Motor nameplate service factor and rated temperature class define the safe range.
**Assumptions:** None beyond OEM-published data being accurate for the specific unit.
**Output:** Rated amps, hp, PF, service factor, temp class
**Uncertainty:** Manufacturing tolerance per OEM QA, typically not independently published — REQUIRES ENGINEERING VALIDATION if precise tolerance needed.
**Reference standard/document:** OEM nameplate/datasheet; possibly cross-referenced to ISO 15551:2023 (which does cover induction motors as an ESP system component) for general performance-rating requirements. NEMA MG-1 not verified in this pass (flagged in 1.5).
**Exact section/table/figure:** N/A / proprietary.
**OEM dependency:** COMPLETE.
**Asset-specific dependency:** Actual installed motor serial/model, actual voltage configuration.
**Failure condition:** No matching OEM data → fail closed.

---
**CALCULATION ID:** `B3_CABLE_VOLTAGE_DROP`
**Name:** Downhole Power Cable Voltage Drop
**Purpose:** Calculate voltage drop across the power cable run to determine actual motor terminal voltage.
**Domain:** OEM/standard electrical
**Formula:** Standard AC voltage-drop relation `Vdrop = I × Z_cable × L`, where Z_cable (resistance + reactance per unit length) is cable-gauge- and temperature-specific.
**Required inputs:** Cable gauge/type, cable length, downhole temperature (affects resistance), operating current, cable resistance/reactance tables
**Optional inputs:** Power factor angle (for full impedance calc rather than resistance-only approximation)
**Units:** V, A, Ω/1000ft (or Ω/km), ft
**Unit conversions:** Resistance tables are often per 1000 ft at a reference temperature — must apply temperature correction.
**Input validity conditions:** Cable resistance/reactance tables must be sourced from cable manufacturer data or IEEE 1019-derived tables (not independently verified in this pass — flagged).
**Operating range:** Valid within the cable's rated ampacity and temperature rating.
**Assumptions:** Steady-state current; does not capture transient/inrush voltage drop.
**Output:** `voltage_drop_v`, `motor_terminal_voltage_v`
**Uncertainty:** Temperature-correction accuracy and cable table accuracy dominate.
**Reference standard/document:** Cable resistance/reactance data conventionally per IEEE 1019 and/or API RP 11S6 (cable testing) and/or OEM cable manufacturer datasheets. **IEEE 1019 content not independently verified in this pass — REQUIRES ENGINEERING VALIDATION before citing specific tables.**
**Exact section/table/figure:** REQUIRES ENGINEERING VALIDATION
**OEM dependency:** Cable manufacturer's resistance/reactance data.
**Asset-specific dependency:** Actual cable run length and gauge as installed.
**Failure condition:** Missing cable spec → fail closed.

---

### SECTION C — Asset-data-dependent calculations

---
**CALCULATION ID:** `C1_SYSTEM_OPERATING_POINT`
**Name:** ESP System Operating Point (Q, PIP)
**Purpose:** Determine actual flow rate and pump intake pressure by intersecting the well inflow performance (IPR) with the ESP's vertical lift performance (VLP) at the current frequency.
**Domain:** Nodal analysis (well + pump system)
**Formula:** No closed-form universal formula — iterative solution for Q where `P_IPR(Q) = P_VLP(Q)` (or equivalent node-balance formulation). The IPR relationship itself (e.g., Vogel, straight-line, composite) is a **peer-reviewed correlation choice**, not a fixed standard formula.
**Required inputs:** Reservoir pressure, productivity index or IPR model + parameters, wellbore geometry, fluid PVT properties, pump curve (B1), frequency (A4)
**Optional inputs:** Skin factor, multiphase flow correlation selection
**Units:** psi, bpd, ft
**Unit conversions:** Consistent depth/pressure datum required (surface vs. datum depth reference).
**Input validity conditions:** IPR model must be selected and validated by the engineer for the specific well/reservoir type — this system must not silently default to a single IPR model.
**Operating range:** Solution Q must fall within both the IPR's valid range and the pump curve's valid range (B1).
**Assumptions:** Steady-state flow; no transient wellbore storage effects.
**Output:** `Q_operating_bpd`, `PIP_psi`
**Uncertainty:** Dominated by IPR/PVT model selection uncertainty — this is inherently an engineering judgment call, not a deterministic single-answer calculation. The service should expose model choice and sensitivity, not just a point answer.
**Reference standard/document:** Nodal-analysis methodology is standard petroleum-engineering practice (textbook: e.g., production engineering references); no single API/ISO standard prescribes the IPR correlation itself. **REQUIRES CLIENT/ENGINEERING SELECTION of IPR and multiphase-flow correlation** — do not invent a default.
**Exact section/table/figure:** N/A
**OEM dependency:** Pump curve (B1).
**Asset-specific dependency:** COMPLETE — reservoir/well data is entirely asset-specific.
**Failure condition:** Missing IPR parameters or no convergent solution → fail closed, flag for engineering review.

---
**CALCULATION ID:** `C2_MOTOR_LOAD_PERCENT`
**Name:** Motor Load Percentage
**Purpose:** Compare measured motor current to nameplate rated current to assess loading status.
**Domain:** Asset + OEM electrical
**Formula:** `%Load = (I_measured / I_rated) × 100`
**Required inputs:** Measured motor current (SCADA/VSD), nameplate rated current (B2)
**Optional inputs:** VSD frequency (if current measured at non-rated frequency, load% interpretation changes — flag rather than silently normalize)
**Units:** A, %
**Unit conversions:** none
**Input validity conditions:** I_measured and I_rated must be from the same phase-reference basis (single-phase reading vs. 3-phase average).
**Operating range:** Nameplate service factor defines acceptable upper bound (typically client-approved threshold, e.g., "flag above 100% of nameplate" — the *threshold* is a client/OEM decision, see Section E).
**Assumptions:** None beyond consistent measurement basis.
**Output:** `motor_load_pct`
**Uncertainty:** SCADA current-transducer accuracy.
**Reference standard/document:** Standard ratio calculation; rated current from OEM nameplate (B2).
**Exact section/table/figure:** N/A
**OEM dependency:** Nameplate rated current.
**Asset-specific dependency:** Real-time measured current.
**Failure condition:** Missing either input → fail closed.

---

### SECTION D — Fluid/PVT-dependent calculations

---
**CALCULATION ID:** `D1_VISCOSITY_CORRECTION`
**Name:** Viscous Liquid Performance Correction (Q, H, η)
**Purpose:** Correct a water-tested OEM pump curve to actual viscous-fluid performance.
**Domain:** PVT + pump hydraulics
**Formula:** Per ANSI/HI 9.6.7 correction-factor methodology: `Q_visc = CQ × Q_water`, `H_visc = CH × H_water`, `η_visc = Cη × η_water`, where CQ, CH, Cη are read from the standard's correction-factor charts as functions of viscosity, flow, and head at BEP.
**Required inputs:** Water-curve (Q,H,η) at BEP (B1), fluid kinematic viscosity at flowing conditions, BEP flow/head at 1.0 cP reference
**Optional inputs:** Non-Newtonian behavior flag (standard applies to Newtonian fluids only — if non-Newtonian, correction is invalid and REQUIRES ENGINEERING VALIDATION of an alternative method)
**Units:** cSt (kinematic viscosity), bpd, ft, %
**Unit conversions:** Viscosity must be converted to cSt at flowing (downhole) temperature, not surface/lab temperature, without correction.
**Input validity conditions:** Per ANSI/HI 9.6.7-2015 scope statement, applicable to radial-flow OH/BB/VS-type pumps, kinematic viscosity approximately 1–4000 cSt (**confirm this bound is unchanged in the 2021 edition before hard-coding** — not independently confirmed in this pass). Applicability to ESP submersible-multistage geometry specifically (vs. the surface-pump types the standard's scope text lists) is **not explicitly confirmed** — ESPs are widely treated as within scope in industry practice, but this package does not assert that as a verified standard-text fact. **Flag: REQUIRES ENGINEERING VALIDATION — confirm ANSI/HI 9.6.7 applicability statement explicitly covers multistage ESP geometry, or use an OEM-published viscosity-correction curve instead if the OEM provides one directly.**
**Operating range:** Outside the standard's stated viscosity/geometry range, do not apply — fail closed.
**Assumptions:** Newtonian fluid behavior.
**Output:** `Q_visc_bpd`, `H_visc_ft`, `eta_visc_pct`
**Uncertainty:** ANSI/HI 9.6.7-2021 itself documents standard deviation for its correction factors and additional guidance on viscous power-consumption uncertainty (per its "what's new" summary) — the exact numeric uncertainty bands were not retrieved in this pass; cite from the purchased standard text.
**Reference standard/document:** ANSI/HI 9.6.7-2021, Rotodynamic Pumps — Guideline for Effects of Liquid Viscosity on Performance.
**Exact section/table/figure:** Correction-factor charts are in the standard's Section 9.6.7.4 area (flowchart/chart figures 9.6.7.4.4a–c, 9.6.7.4.5a–b per table-of-contents evidence found) — **exact figure numbers should be re-confirmed against the purchased standard**, not hard-coded from this secondary listing alone.
**OEM dependency:** Base water curve (B1).
**Asset-specific dependency:** Flowing-condition viscosity (from PVT table).
**Failure condition:** Viscosity or base curve missing, or viscosity outside standard's valid range → fail closed.

---
**CALCULATION ID:** `D2_FREE_GAS_FRACTION`
**Name:** Free Gas Fraction at Pump Intake
**Purpose:** Determine in-situ gas volume fraction at intake conditions, required to correct pump performance for gas interference/gas locking risk.
**Domain:** PVT
**Formula:** No single universal formula — depends on the selected PVT correlation set (e.g., Standing correlation for solution GOR/Bo, or client-specific PVT lab data/EOS model) to compute gas-oil ratio in solution at intake P/T, then combine with total produced GOR to get free-gas volume fraction at intake conditions.
**Required inputs:** Reservoir fluid PVT properties (bubble point, solution GOR, Bo, Bg — from lab PVT report or correlation), intake pressure (C1), intake temperature
**Optional inputs:** Water cut (affects mixture properties)
**Units:** psi, °F, scf/bbl, dimensionless fraction
**Unit conversions:** Standard oilfield PVT unit set.
**Input validity conditions:** Must use asset-specific PVT data (lab report) where available; a generic correlation is a fallback, not a default, and must be flagged as such when used.
**Operating range:** Correlation-specific validity ranges (e.g., API gravity range, GOR range, temperature range) apply and vary by correlation — **not stated here to avoid presenting an unverified numeric range as fact.**
**Assumptions:** Depends entirely on which correlation/model is selected.
**Output:** `free_gas_fraction_intake`
**Uncertainty:** Can be large (correlation-to-lab-data mismatch is a well-known industry problem) — this should be flagged prominently in any UI, not presented as a precise number.
**Reference standard/document:** Peer-reviewed PVT correlations (priority tier 6) or lab PVT data (priority tier 5/6, asset-specific) — **no API/ISO standard prescribes a single mandatory correlation.** Selection is a client/engineering decision. **REQUIRES ENGINEERING VALIDATION / CLIENT SPECIFICATION of which correlation(s) are approved for use.**
**Exact section/table/figure:** N/A — depends on selected literature source.
**OEM dependency:** None directly (may inform gas separator selection, see D3).
**Asset-specific dependency:** COMPLETE.
**Failure condition:** No PVT data/correlation selected → fail closed; do not default silently to any single correlation.

---
**CALCULATION ID:** `D3_GAS_HANDLING_DERATING`
**Name:** Pump Performance Derating for Free Gas
**Purpose:** Estimate pump head/efficiency degradation due to free gas at intake, and/or gas separator efficiency.
**Domain:** PVT + OEM
**Formula:** No universal formula identified/verified in this pass. Gas-handling derating is typically based on either (a) an OEM-specific gas-handling curve for the specific pump/gas-separator combination, or (b) published literature correlations (e.g., Turpin-type correlations) whose applicability is equipment-specific.
**Required inputs:** Free gas fraction (D2), OEM gas-handling curve or gas separator efficiency spec
**Optional inputs:** none
**Units:** % derating, dimensionless gas fraction
**Unit conversions:** none
**Input validity conditions:** REQUIRES ENGINEERING VALIDATION
**Operating range:** REQUIRES ENGINEERING VALIDATION
**Assumptions:** REQUIRES ENGINEERING VALIDATION
**Output:** `head_derating_pct` (or equivalent)
**Uncertainty:** High — this is one of the least standardized calculations in ESP engineering.
**Reference standard/document:** No current API/ISO standard was identified in this pass that prescribes a mandatory gas-handling derating formula. **Any gas-handling formula in the service MUST be OEM-sourced for the specific separator/pump model, or explicitly cited to a named peer-reviewed paper with its stated validity range — do not implement a generic formula from training-data memory.**
**Exact section/table/figure:** N/A
**OEM dependency:** COMPLETE if OEM curve route is used.
**Asset-specific dependency:** Free gas fraction, equipment configuration.
**Failure condition:** No OEM curve and no client-approved literature correlation on file → this calculation should not run; output `"REQUIRES ENGINEERING VALIDATION: no approved gas-handling model configured"`.

---
**CALCULATION ID:** `D4_FLUID_MIXTURE_SG`
**Name:** Flowing Fluid Mixture Specific Gravity
**Purpose:** Compute blended SG of oil/water/gas mixture at flowing conditions for use in A1/A2.
**Domain:** PVT
**Formula:** For liquid-only mixture (no free gas): `SG_mix = WC × SG_water + (1 − WC) × SG_oil`, where WC = water cut (fraction). This is a basic mass/volume mixture rule (fundamental), valid **only** when no free gas is present at the point of measurement — if free gas exists, the mixture density calculation must incorporate gas fraction (D2) and is no longer this simple weighted average.
**Required inputs:** Water cut (WC), oil SG (or °API), water SG (produced water density, often ≠ 1.0 due to salinity — must use actual produced-water SG, not assume fresh water)
**Optional inputs:** Gas fraction, if present (routes to a more complex three-phase mixture calc — REQUIRES ENGINEERING VALIDATION for the three-phase formula, not covered here)
**Units:** dimensionless SG, fraction WC
**Unit conversions:** °API → SG: `SG = 141.5/(131.5 + °API)` (standard API gravity definition — fundamental, not a fitted correlation)
**Input validity conditions:** WC between 0 and 1; SG values > 0
**Operating range:** Single-phase liquid only, as noted.
**Assumptions:** No volume-of-mixing correction (ideal mixing assumed).
**Output:** `sg_mix`
**Uncertainty:** Produced-water SG is often assumed rather than measured — flag this as a common data-quality gap.
**Reference standard/document:** Fundamental fluid-property definitions (API gravity is defined by API convention, universally standard, not a proprietary calculation method).
**Exact section/table/figure:** N/A
**OEM dependency:** None
**Asset-specific dependency:** WC, oil SG, water SG all asset-specific.
**Failure condition:** Missing WC or component SGs → fail closed.

---

### SECTION E — Client-approved-limit calculations

These calculations compare a computed or measured value against a **limit that is not universally fixed by a public standard** — it is either OEM-recommended, ISO 15551:2023's ROR concept (whose exact numeric method is in a paywalled annex not verified here), or a client-specific operating philosophy. **None of these limits should be hard-coded from general industry "rules of thumb."**

---
**CALCULATION ID:** `E1_RECOMMENDED_OPERATING_RANGE_CHECK`
**Name:** Operating Point vs. Recommended Operating Range (ROR)
**Purpose:** Flag whether current operating rate is inside the pump's safe/recommended envelope.
**Domain:** Client-approved limits + standard framework
**Formula:** `Q_min_ROR ≤ Q_actual ≤ Q_max_ROR` → boolean pass/fail, plus `%ROR` position metric if desired.
**Required inputs:** Q_actual (C1), Q_min_ROR and Q_max_ROR
**Optional inputs:** none
**Units:** bpd
**Unit conversions:** none
**Input validity conditions:** Q_min_ROR/Q_max_ROR must be sourced from (in priority order): (1) OEM published ROR for the specific pump model, (2) ISO 15551:2023 informative-annex methodology if independently applied by a qualified engineer, (3) client-approved operating envelope on file for the asset. **This package does not supply default numeric ROR bounds — none were verified from a retrievable source.**
**Operating range:** N/A — this calculation defines the range check itself.
**Assumptions:** ROR bounds are current for the actual installed stage/frequency configuration.
**Output:** `in_ror_bool`, `pct_of_ror_range`
**Uncertainty:** N/A (boolean/categorical)
**Reference standard/document:** ISO 15551:2023 (informative annex establishing ROR methodology — concept confirmed, numeric method not verified); OEM ROR specification (asset-specific); client operating philosophy document (E-category, asset-specific).
**Exact section/table/figure:** REQUIRES ENGINEERING VALIDATION (purchase/access ISO 15551:2023 informative annex directly)
**OEM dependency:** HIGH if OEM ROR is the source.
**Asset-specific dependency:** HIGH if client-approved envelope is the source.
**Failure condition:** No ROR bounds on file for the asset/equipment → do not run the check; flag `"REQUIRES ENGINEERING VALIDATION: no ROR configured for this asset"`.

---
**CALCULATION ID:** `E2_VIBRATION_LIMIT_CHECK`
**Name:** ESP Vibration vs. Limit
**Purpose:** Compare measured/monitored vibration to acceptable limits.
**Domain:** Client-approved limits + standard framework
**Formula:** `Vib_measured ≤ Vib_limit` → boolean; trending slope optionally computed (standard statistical trend, not a standards-defined formula).
**Required inputs:** Measured vibration (downhole sensor or surface, per available instrumentation), vibration limit
**Optional inputs:** Frequency-domain (FFT) breakdown for diagnostic use
**Units:** Per API RP 11S8 convention (typically in/s or g, depending on sensor type — exact units and limit values not independently verified in this pass)
**Unit conversions:** REQUIRES ENGINEERING VALIDATION (confirm sensor units match standard's stated units)
**Input validity conditions:** Vibration limit must be sourced from API RP 11S8 or OEM/client specification — **exact numeric limits in API RP 11S8 were not retrieved in this pass (document is paywalled); do not hard-code a limit value from memory.**
**Operating range:** N/A
**Assumptions:** Sensor is correctly calibrated and positioned per API RP 11S8 testing guidance (not independently verified here).
**Output:** `vib_ok_bool`
**Uncertainty:** Sensor accuracy; mounting/location sensitivity.
**Reference standard/document:** API RP 11S8, Electric Submersible System Vibrations.
**Exact section/table/figure:** REQUIRES ENGINEERING VALIDATION
**OEM dependency:** Sensor spec, possibly OEM-specific vibration limits tighter than the RP's general guidance.
**Asset-specific dependency:** Client-approved limit if different from RP/OEM default.
**Failure condition:** No limit configured → fail closed / flag for validation.

---
**CALCULATION ID:** `E3_MOTOR_TEMPERATURE_LIMIT_CHECK`
**Name:** Motor Winding/Downhole Temperature vs. Limit
**Purpose:** Flag motor thermal risk.
**Domain:** Client-approved limits + OEM
**Formula:** `T_measured ≤ T_limit` → boolean
**Required inputs:** Measured motor/downhole temperature, temperature limit (OEM insulation class rating, adjusted for client-approved safety margin)
**Optional inputs:** none
**Units:** °F or °C
**Unit conversions:** Standard conversion if mixed sources.
**Input validity conditions:** T_limit must come from OEM nameplate/insulation class (B2) and/or client-approved derating policy — not a generic assumed value.
**Operating range:** N/A
**Assumptions:** Sensor placement is representative of actual winding temperature (often it is a housing/oil temperature proxy, not true winding temp — flag this distinction).
**Output:** `temp_ok_bool`
**Uncertainty:** Proxy-sensor offset from true winding temperature is typically significant and OEM-specific.
**Reference standard/document:** OEM motor nameplate/insulation class; client-approved thermal derating policy.
**Exact section/table/figure:** N/A / proprietary
**OEM dependency:** HIGH
**Asset-specific dependency:** Client policy margin.
**Failure condition:** No limit on file → fail closed.

---

### SECTION F — Diagnostic feature calculations

These are pattern/trend features used for troubleshooting (aligned with API RP 11S troubleshooting scope) rather than deterministic physical calculations with a single "correct" numeric answer. **All threshold values here are heuristic/statistical unless a specific standard/OEM source is cited — flagged accordingly.**

---
**CALCULATION ID:** `F1_AMPS_TREND_SLOPE`
**Name:** Motor Current Trend Slope
**Purpose:** Detect gradual motor-load drift (e.g., scale buildup, pump wear) via slope of amps over a rolling time window.
**Domain:** Diagnostic / statistical
**Formula:** Standard linear-regression slope of measured current vs. time over a defined window: `slope = Σ((t−t̄)(I−Ī)) / Σ((t−t̄)²)`
**Required inputs:** Time-series of measured motor current, window length
**Optional inputs:** Outlier-rejection method
**Units:** A/day (or A/hour)
**Unit conversions:** none
**Input validity conditions:** Minimum data density/window length for a statistically meaningful slope — **specific minimum sample count is a methodology choice, REQUIRES ENGINEERING VALIDATION / client specification, not invented here.**
**Operating range:** N/A
**Assumptions:** Approximately linear trend over the window; not valid across a step-change event (startup, frequency change) without segmenting the data.
**Output:** `amps_trend_slope`
**Uncertainty:** Sensitive to window length and outlier handling — both are configuration choices, not standard-defined.
**Reference standard/document:** Standard statistical method (linear regression); troubleshooting *use* of amps trends is consistent with API RP 11S's general troubleshooting scope, but the RP does not (based on available scope text) prescribe this specific statistical formula.
**Exact section/table/figure:** N/A
**OEM dependency:** None for the math; interpretation thresholds are OEM/client-specific.
**Asset-specific dependency:** The trend itself.
**Failure condition:** Insufficient data density → output null with `"insufficient data for trend"`, not a misleading slope from sparse data.

---
**CALCULATION ID:** `F2_CYCLIC_RUN_PATTERN_DETECTION`
**Name:** Pump-Off / Cyclic Operation Detection
**Purpose:** Identify cyclic run/stop patterns indicative of pump-off control or fluid-level-limited operation.
**Domain:** Diagnostic / statistical
**Formula:** No universal formula — typically state-change counting (run/stop transitions per time window) against a client-defined cyclic-frequency threshold.
**Required inputs:** Run-status time series
**Optional inputs:** Amperage profile per cycle (for further classification)
**Units:** cycles/day
**Unit conversions:** none
**Input validity conditions:** REQUIRES ENGINEERING VALIDATION for what cycle count constitutes "excessive" — this is an operational/reliability policy choice, not a standard.
**Operating range:** N/A
**Assumptions:** Run-status data is reliable (no SCADA gaps misread as stop events).
**Output:** `cycles_per_day`, `cyclic_flag_bool`
**Uncertainty:** SCADA data-quality dependent.
**Reference standard/document:** No standard identified; aligns with general ESP troubleshooting practice (API RP 11S scope) but not a cited formula within it. **REQUIRES ENGINEERING VALIDATION for threshold.**
**Exact section/table/figure:** N/A
**OEM dependency:** None
**Asset-specific dependency:** Full — run/stop data and threshold policy.
**Failure condition:** Missing run-status data → fail closed.

---
**CALCULATION ID:** `F3_LOAD_FLAG`
**Name:** Underload/Overload Flag
**Purpose:** Flag abnormal motor loading (potential gas lock, worn pump = underload; scale/mechanical drag = overload) using C2 output against client thresholds.
**Domain:** Diagnostic
**Formula:** `IF motor_load_pct < Underload_Threshold_pct THEN flag "underload"`; `IF motor_load_pct > Overload_Threshold_pct THEN flag "overload"`
**Required inputs:** motor_load_pct (C2), client-approved thresholds
**Optional inputs:** none
**Units:** %
**Unit conversions:** none
**Input validity conditions:** Thresholds must be on file per asset/fleet policy — **no default thresholds are asserted here.**
**Operating range:** N/A
**Assumptions:** none beyond C2's assumptions
**Output:** `load_flag` (enum: normal/underload/overload)
**Uncertainty:** Inherits C2 uncertainty.
**Reference standard/document:** Client-approved operating philosophy (E-category); no public standard prescribes universal underload/overload % thresholds for ESP motors in this research pass.
**Exact section/table/figure:** N/A
**OEM dependency:** Possible OEM-recommended thresholds as a starting point, still requiring client approval.
**Asset-specific dependency:** Full.
**Failure condition:** No thresholds configured → do not run; flag for configuration.

---

### SECTION G — Reliability/maintenance calculations

---
**CALCULATION ID:** `G1_FAILURE_CLASSIFICATION`
**Name:** ESP Failure Classification (Teardown-Based)
**Purpose:** Classify pulled-equipment failure cause using a standardized taxonomy for fleet reliability analysis.
**Domain:** Reliability
**Formula:** N/A — categorical classification against a standard taxonomy, not a numeric calculation.
**Required inputs:** Teardown report data (per API RP 11S1 form structure), failure observation codes
**Optional inputs:** Photos, component-level findings
**Units:** N/A (categorical)
**Unit conversions:** N/A
**Input validity conditions:** Teardown report must follow the API RP 11S1 form structure for classification to be comparable across the fleet/industry.
**Operating range:** N/A
**Assumptions:** Teardown findings are accurately recorded by qualified personnel.
**Output:** `failure_category` (per API RP 11S1 taxonomy — exact category list not independently retrieved in this pass; **REQUIRES ENGINEERING VALIDATION to enumerate the exact taxonomy from the RP 11S1 form**)
**Uncertainty:** Classification is subject to teardown-analyst judgment; not independently verifiable without physical inspection.
**Reference standard/document:** API RP 11S1, Electrical Submersible Pump Teardown Report.
**Exact section/table/figure:** REQUIRES ENGINEERING VALIDATION (need direct access to the RP 11S1 form)
**OEM dependency:** Teardown often performed at OEM service center — data provenance should be tracked.
**Asset-specific dependency:** Full — this is inherently per-unit data.
**Failure condition:** No teardown report → cannot classify; leave failure cause as "undetermined," not inferred from indirect data alone.

---
**CALCULATION ID:** `G2_RUN_LIFE_MTBF`
**Name:** Run Life / Mean Time Between Failures
**Purpose:** Standard reliability metric for fleet performance tracking.
**Domain:** Reliability statistics
**Formula:** `Run_Life_days = Pull_Date − Install_Date` (per unit); `MTBF = Σ(Run_Life_days) / Number_of_Failures` over a defined population and time window (standard reliability-engineering definition).
**Required inputs:** Install date, pull date, failure/pull-reason classification (to distinguish failure pulls from planned/non-failure pulls — a critical and often-mishandled distinction)
**Optional inputs:** Censoring treatment for units still running (standard survival-analysis consideration)
**Units:** days
**Unit conversions:** none
**Input validity conditions:** Only "failure" pulls should count toward failure-driven MTBF; workover/non-failure pulls must be excluded or separately tracked, per the classification from G1.
**Operating range:** N/A
**Assumptions:** Population definition (which wells/time window) must be explicit — MTBF is meaningless without a clearly bounded population.
**Output:** `mtbf_days`, `run_life_days` (per unit)
**Uncertainty:** Small-population MTBF is statistically unstable — should report population size (n) alongside the metric, not a bare number.
**Reference standard/document:** Standard reliability-engineering definition (fundamental statistics); classification input governed by API RP 11S1.
**Exact section/table/figure:** N/A for the statistical formula itself.
**OEM dependency:** None for the math.
**Asset-specific dependency:** Full — install/pull dates and cause classification per unit.
**Failure condition:** Missing install or pull date → exclude unit from calculation, do not impute dates.

---
**CALCULATION ID:** `G3_MTTR`
**Name:** Mean Time To Repair/Replace
**Purpose:** Track operational responsiveness/logistics performance.
**Domain:** Reliability/maintenance statistics
**Formula:** `MTTR = Σ(Pull_Date_to_Restart_Date) / Number_of_Events` over a defined population.
**Required inputs:** Pull date, restart (new unit online) date
**Optional inputs:** Downtime cause breakdown (logistics vs. engineering vs. weather, etc.)
**Units:** days (or hours)
**Unit conversions:** none
**Input validity conditions:** Population/time-window must be explicit.
**Operating range:** N/A
**Assumptions:** none beyond data completeness
**Output:** `mttr_days`
**Uncertainty:** Same small-population caveat as G2.
**Reference standard/document:** Standard maintenance-engineering definition (fundamental).
**Exact section/table/figure:** N/A
**OEM dependency:** None
**Asset-specific dependency:** Full
**Failure condition:** Missing dates → exclude event, do not impute.

---

## 3. Calculations That CANNOT Be Safely Standardized Without OEM-Specific Data

- **B1 (pump curve lookup)** — every pump model/stage design has a unique curve; there is no generic ESP pump curve.
- **B2 (motor curve/nameplate)** — motor performance is unit/model-specific.
- **B3 (cable voltage drop)** — depends on manufacturer-specific cable construction data.
- **D3 (gas handling derating)** — dependent on the specific gas separator/pump combination; no universal correlation was verified as authoritative.
- **E1 (ROR check)** — numeric bounds are OEM- or ISO-annex-sourced per equipment model, not universal.
- **E2 (vibration limit)**, **E3 (temperature limit)** — limits are OEM/client-specific even though the *framework* (API RP 11S8) is standard.
- Any wear/degradation correction to a "new equipment" OEM curve — not covered by any standard identified in this pass.

## 4. Master Input Data Requirements Table

| Field | Description | Unit | Req/Opt | Source | Frequency | Validity requirement | Used by | Authority |
|---|---|---|---|---|---|---|---|---|
| flowing_pressure_diff | Pump discharge − intake ΔP | psi | Required | SCADA/gauge | Continuous/periodic | Same timestamp window, same asset | A1 | Fundamental physics |
| fluid_sg_flowing | Flowing mixture SG | dimensionless | Required | D4 output / lab | Per calc | Positive, updated with WC changes | A1,A2 | Fundamental / PVT |
| flow_rate_q | Produced flow rate | bpd | Required | Test/allocation/estimate | Periodic (well test) | Flowing-condition basis | A2,A5,C1,E1 | Asset data |
| total_dynamic_head | Total head across pump | ft | Required | Derived (C1) or measured | Per calc | Consistent datum | A2,A3 | Derived |
| pump_efficiency | Hydraulic efficiency at Q | % | Required | OEM curve (B1) | Per calc | Within curve's valid Q range | A3 | OEM |
| stage_count | Number of pump stages installed | count | Required | Equipment record | Static (per install) | Matches physical build | B1,A3 | Asset/OEM |
| operating_frequency | VSD drive frequency | Hz | Required | SCADA | Continuous | Within OEM/motor rated range | A4,B1,B2 | Asset data |
| base_curve_frequency | Frequency at which OEM curve was tested | Hz | Required | OEM datasheet | Static | Must be confirmed, not assumed 60Hz | A4 | OEM |
| motor_measured_current | Measured motor amps | A | Required | SCADA/VSD | Continuous | Same phase basis as rated | C2,F1,F3 | Asset data |
| motor_rated_current | Nameplate rated amps | A | Required | OEM nameplate | Static | Matches installed serial | B2,C2 | OEM |
| kinematic_viscosity | Fluid viscosity at flowing T | cSt | Required if D1 used | Lab/PVT correlation | Periodic | Within HI 9.6.7 valid range | D1 | PVT/lab |
| water_cut | Produced water fraction | fraction | Required | Test separator | Periodic (well test) | 0–1 | D4 | Asset data |
| oil_gravity | Stock-tank oil gravity | °API | Required | Lab/PVT report | Static/periodic | Positive | D4 | PVT/lab |
| produced_water_sg | Actual produced-water density | SG | Required | Lab | Periodic | Positive; not defaulted to 1.0 | D4 | PVT/lab |
| reservoir_pressure | Static reservoir pressure | psi | Required for C1 | Well test/buildup | Periodic | Datum-consistent | C1 | Asset data |
| ipr_model_selection | Chosen IPR correlation | enum | Required for C1 | Engineering decision | Static/per revision | Explicit, logged | C1 | Client/engineering |
| vibration_measured | Measured vibration | in/s or g | Required if E2 used | Sensor | Continuous | Per API RP 11S8 sensor guidance | E2 | Asset/standard |
| motor_temperature | Measured motor/housing temp | °F/°C | Required if E3 used | Sensor | Continuous | Sensor placement documented | E3 | Asset/OEM |
| install_date | ESP install date | date | Required | Work order | Static per run | Valid calendar date | G2 | Asset data |
| pull_date | ESP pull date | date | Required (on pull) | Work order | Static per run | ≥ install_date | G2,G3 | Asset data |
| failure_classification | Teardown-derived cause | enum | Required for MTBF | Teardown report | Per pull | Per API RP 11S1 taxonomy | G1,G2 | API RP 11S1 |

## 5. OEM Data Requirements Table

| Field | Description | Required for |
|---|---|---|
| pump_model_id | Exact OEM pump model/series | B1, A3, A5 |
| pump_curve_dataset | Digitized (Q,H,η,BHP) at base frequency | B1 |
| pump_curve_base_frequency | Test frequency of curve | A4, B1 |
| pump_ror_bounds | OEM-recommended min/max flow | E1 |
| motor_model_id | Exact OEM motor model/serial | B2 |
| motor_nameplate_data | V, A, hp, PF, service factor, insulation class | B2, C2, E3 |
| motor_slip_curve | Slip vs. load (for actual shaft speed) | A4 (optional refinement) |
| cable_type_gauge | Cable construction/gauge | B3 |
| cable_impedance_table | R/X per length, per temperature | B3 |
| gas_separator_model | If installed | D3 |
| gas_handling_curve | OEM-specific, if published | D3 |
| vibration_limit_oem | OEM-specific vibration threshold, if tighter than RP default | E2 |

## 6. PVT/Fluid Data Requirements Table

| Field | Description | Required for |
|---|---|---|
| bubble_point_pressure | Pb | D2 |
| solution_gor_correlation_or_lab | Rs(P,T) | D2 |
| oil_fvf | Bo | D2 |
| gas_fvf | Bg | D2 |
| kinematic_viscosity_vs_temp | μ(T) curve | D1 |
| oil_gravity_api | °API | D4 |
| produced_water_sg | Water density | D4 |
| water_cut | WC | D4 |
| pvt_source_type | Lab report vs. correlation (and which) | D2, D1, logged for uncertainty |

## 7. Well Data Requirements Table

| Field | Description | Required for |
|---|---|---|
| reservoir_pressure | Static BHP | C1 |
| productivity_index_or_ipr_params | PI or Vogel/composite params | C1 |
| perforation/completion_depth | Datum reference | A1, C1 |
| wellbore_deviation_survey | For true vertical depth / friction calcs | C1 (if VLP includes friction) |
| tubing_id | For VLP friction losses | C1 |
| test_flow_rate_history | Periodic well tests | C1 validation |
| fluid_level | Casing annulus level, if measured | Cross-check for PIP (C1) |

## 8. ESP Equipment Data Requirements Table

| Field | Description | Required for |
|---|---|---|
| pump_model_and_stage_count | Installed configuration | B1, A3, A5, E1 |
| motor_model_and_config | Series/parallel, voltage | B2, C2, E3 |
| protector_seal_model | Component ID (troubleshooting context) | API RP 11S troubleshooting scope, not directly in numeric calcs above |
| gas_separator_model_if_any | Component ID | D3 |
| cable_spec | Gauge, type, length | B3 |
| install_date | — | G2 |
| pull_date | — | G2, G3 |
| setting_depth | — | A1, C1 |
| sensor_package | Downhole gauge type/capability (P, T, vibration) | C1, E2, E3 |

## 9. Calculation Dependency Matrix

| Calculation | Inputs | Standard | OEM data | Asset data | PVT data |
|---|---|---|---|---|---|
| A1 Head↔Pressure | ΔP, SG | Fundamental physics | — | SG (from D4) | ✓ |
| A2 Hydraulic Power | Q, H, SG | Fundamental physics | — | ✓ | ✓ |
| A3 BHP | WHP, η | Fundamental + API RP 11S2 (curve provenance) | ✓ (η curve) | — | — |
| A4 Affinity Laws | Q1,H1,BHP1,N1,N2 | Fundamental (HI general ref) | ✓ (base curve) | ✓ (N2) | — |
| A5 %BEP | Q_actual, Q_BEP | Standard metric | ✓ (Q_BEP) | ✓ (Q_actual) | — |
| B1 Pump curve | Q, model | API RP 11S2 (test methodology) | ✓✓✓ | ✓ (model installed) | — |
| B2 Motor lookup | model | ISO 15551:2023 (motor as component) | ✓✓✓ | ✓ (model installed) | — |
| B3 Cable V-drop | I, cable spec | IEEE 1019 (unverified)/API RP 11S6 | ✓✓✓ | ✓ (length) | — |
| C1 Operating point | reservoir, pump curve | Nodal analysis (textbook) | ✓ (B1) | ✓✓✓ | ✓ |
| C2 Motor load% | I_meas, I_rated | Standard ratio | ✓ (B2) | ✓ (I_meas) | — |
| D1 Viscosity correction | curve, viscosity | ANSI/HI 9.6.7-2021 | ✓ (B1) | — | ✓✓✓ |
| D2 Free gas fraction | PVT, PIP | Peer-reviewed correlation (client-selected) | — | ✓ (PIP from C1) | ✓✓✓ |
| D3 Gas derating | gas fraction, sep. curve | Unverified/OEM | ✓✓✓ | — | ✓ (D2) |
| D4 Mixture SG | WC, oil/water SG | Fundamental | — | ✓✓✓ | ✓ |
| E1 ROR check | Q_actual, bounds | ISO 15551:2023 annex (unverified numerics) | ✓ (bounds) | ✓ (bounds/policy) | — |
| E2 Vibration | measured, limit | API RP 11S8 (numerics unverified) | ✓ (limit) | ✓ (measured) | — |
| E3 Temp limit | measured, limit | OEM/client | ✓ (limit) | ✓ (measured) | — |
| F1 Amps trend | time series | Statistical (fundamental) | — | ✓✓✓ | — |
| F2 Cyclic detection | run status | Statistical (fundamental) | — | ✓✓✓ | — |
| F3 Load flag | C2, thresholds | Client policy | ✓ (optional starting pt) | ✓✓✓ | — |
| G1 Failure class | teardown data | API RP 11S1 | ✓ (if OEM teardown) | ✓✓✓ | — |
| G2 MTBF | dates, G1 | Statistical (fundamental) | — | ✓✓✓ | — |
| G3 MTTR | dates | Statistical (fundamental) | — | ✓✓✓ | — |

---

## 10. Minimum Dataset for a Deterministic Single-Asset Service

To implement A1–A5, B1–B3, C1–C2, D1/D4, E1–E3, G2–G3 for **one well**:

1. OEM pump curve (digitized Q,H,η,BHP at a known base frequency) for the exact installed model/stage count.
2. OEM motor nameplate data for the exact installed model.
3. Cable spec (gauge, length, type) — plus a sourced impedance table (OEM or verified IEEE 1019 data).
4. Real-time or periodic SCADA data: current, frequency, discharge pressure, intake pressure (or proxy).
5. Fluid basics: water cut, oil gravity, produced water SG (measured, not assumed).
6. Reservoir pressure and a chosen, documented IPR model with parameters.
7. OEM-published or client-approved ROR bounds for the installed pump.
8. API RP 11S8-referenced vibration limit (or OEM/client limit) if vibration monitoring exists.
9. Motor temperature limit (OEM insulation class + client margin).
10. Install date (for run-life tracking from day one).
11. If viscosity correction is needed: kinematic viscosity at flowing temperature, confirmed to be within ANSI/HI 9.6.7's valid range.

**Explicitly NOT achievable with a "minimum" dataset, even for one asset:** D2/D3 (free-gas/gas-handling) require either lab PVT data or an engineering-approved correlation choice — this is a judgment call that must be made and logged by a qualified engineer, not defaulted by the service. G1 (failure classification) requires an actual teardown event; it has no value until the first failure/pull occurs.

## 11. Additional Dataset for Multi-Asset Production Deployment

1. A **pump/motor/cable master catalog** (all OEM curves and nameplates the fleet actually uses), version-controlled, with revision dates — not one-off per-well entry.
2. A **standards/reference version registry** (this document's Section 1, kept current — standards get reaffirmed/withdrawn; API RP 11S4's withdrawal, discovered in this research pass, is a concrete example of why this must be actively maintained, not captured once).
3. Fleet-wide **failure taxonomy governance** aligned to API RP 11S1 so G1/G2 are comparable across wells/fields.
4. A **client-approved limits repository** (E-section thresholds) per asset or per asset class, with an approval/change-log trail — these are not universal and must not silently default across the fleet.
5. **PVT correlation governance**: an approved list of correlations per field/reservoir, with documented validity ranges, so D1/D2 don't silently apply an out-of-range correlation.
6. **Data quality/gap handling policy**: explicit fail-closed behavior (as specified per calculation above) implemented consistently, with an audit trail of every "REQUIRES ENGINEERING VALIDATION" flag raised and resolved.
7. **Unit-system governance**: consistent psi/ft/bpd/°F oilfield units enforced at ingestion, with conversion audit logging (a common source of silent error at multi-asset scale).
8. **Curve digitization pipeline** with version control, since B1/B2/B3 depend entirely on correctly digitized OEM source documents — errors here propagate into every downstream calculation.
9. **Sensor metadata registry** (type, location, calibration date) per asset, since E2/E3 depend on knowing what a given sensor actually measures and how well it represents the modeled quantity (see the winding-vs-housing-temperature caveat under E3).

---

## 12. Summary of Explicit "REQUIRES ENGINEERING VALIDATION" Flags Raised in This Package

- API RP 11S / 11S1 / 11S2 / 11S3 / 11S8 exact current editions, reaffirmation dates, and section/table/figure numbers — sourced from third-party catalogs, not api.org directly.
- API RP 11S4 confirmed **withdrawn** — any legacy sizing formulas historically drawn from it need a current replacement source.
- ISO 15551:2023 ROR annex numeric methodology — existence confirmed, content not retrieved (paywalled).
- ANSI/HI 9.6.7-2021's exact viscosity/geometry validity range and figure numbers — inferred from the 2015 edition's public scope text and the 2021 TOC; not confirmed verbatim from the current purchased standard.
- Whether ANSI/HI 9.6.7's stated pump types explicitly include multistage ESP geometry, or whether this is industry-practice extension rather than standard-text fact.
- API RP 11S8 numeric vibration limits and units.
- IEEE 1019 cable data content (only cross-referenced, not independently reviewed).
- NEMA MG-1 applicability to ESP motors — not researched in this pass.
- API STD 610 / ISO 13709 applicability to downhole ESP — likely not applicable (surface-pump standard); flagged rather than assumed.
- Any PVT correlation selection (Standing, Vasquez-Beggs, Turpin gas-handling, etc.) — these are literature choices requiring explicit client/engineering sign-off, not defaults.
- Gas-handling derating formula — no current authoritative universal formula identified; must be OEM- or literature-sourced per asset.
- API RP 11S1 exact failure-classification taxonomy — form structure referenced, exact category list not retrieved.
- All numeric limits/thresholds in Section E (ROR bounds, vibration limits, temperature limits, load% thresholds, cyclic-count thresholds) — none are asserted as universal; all require a sourced, on-file value per asset/fleet before the corresponding calculation can run.
