# Backend Response Format Quick Reference
## Visual Guide for Frontend Developers

---

## 🔄 Streaming Flow Diagram

```
User Query: "Why is production declining?"
         ↓
┌────────────────────────────────────────────────────────────┐
│  POST /api/ui/agent/stream                                 │
│  { asset_id: "FS-031", user_query: "..." }                │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│  Backend LangGraph Supervisor Pipeline                     │
│  ┌──────────────────────────────────────────────┐         │
│  │ 1. Intent Router → OP02_PRODUCTION_DECLINE   │         │
│  │ 2. Resolve Asset → Load FS-031 context       │         │
│  │ 3. Data Quality Gate → Validate telemetry    │         │
│  │ 4. Specialists → Run engineering calcs        │         │
│  │ 5. Evidence Collector → Build audit pack     │         │
│  │ 6. Advisory Synthesizer → Format response    │         │
│  └──────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────┘
         ↓ (NDJSON Stream)
┌────────────────────────────────────────────────────────────┐
│  Event 1: {"type":"status", "stage":"INITIATING"}         │
│  Event 2: {"type":"text_delta", "delta":"### Diag..."}    │
│  Event 3: {"type":"text_delta", "delta":"nostic ..."}     │
│  Event 4: {"type":"advisory", "advisory":{...}}            │
│  Event 5: {"type":"generative_ui", "data":[...]}           │
│  Event 6: {"type":"done"}                                  │
└────────────────────────────────────────────────────────────┘
         ↓ (Frontend Parser)
┌────────────────────────────────────────────────────────────┐
│  React State Updates                                       │
│  ┌──────────────────────────────────────────────┐         │
│  │ setMessages() called for each event          │         │
│  │ - Append text chunks to markdown buffer      │         │
│  │ - Store advisory payload                     │         │
│  │ - Store chart data                           │         │
│  │ - Update loading state                       │         │
│  └──────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│  UI Rendering                                              │
│  ┌──────────────────────────────────────────────┐         │
│  │ MarkdownBlock: Formatted diagnostic text     │         │
│  │ PlotlyChartBlock: Interactive trend chart    │         │
│  │ AdvisoryActionCard: Recommendation badge     │         │
│  │ Evidence Drawer Button: "View Pack"          │         │
│  └──────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────┘
```

---

## 📊 Response Format Examples

### Example 1: Text Delta Event (Markdown Streaming)

**Backend sends:**
```json
{"type":"text_delta","delta":"### 🛡️ Diagnostic Summary\n\n**Assessment:** Production"}
{"type":"text_delta","delta":" rate declined from 1650 BPD to 1350 BPD.\n\n**Diagnosis"}
{"type":"text_delta","delta":" Details:** Root cause identified as gas interference.\n\n"}
```

**Frontend accumulates:**
```
Message.textDelta = "### 🛡️ Diagnostic Summary\n\n**Assessment:** Production rate declined from 1650 BPD to 1350 BPD.\n\n**Diagnosis Details:** Root cause identified as gas interference.\n\n"
```

**ReactMarkdown renders:**
```
### 🛡️ Diagnostic Summary

**Assessment:** Production rate declined from 1650 BPD to 1350 BPD.

**Diagnosis Details:** Root cause identified as gas interference.
```

---

### Example 2: Plotly Chart Event

**Backend sends:**
```json
{
  "type": "generative_ui",
  "kind": "plotly_chart",
  "run_id": "RUN-UI-a7b3f2e1",
  "chart_id": "chart-001",
  "title": "24-Hour Production & Pressure Trend",
  "data": [
    {
      "x": ["08:00", "10:00", "12:00", "14:00", "16:00"],
      "y": [1650, 1580, 1520, 1450, 1350],
      "type": "scatter",
      "mode": "lines+markers",
      "name": "Flow Rate (BPD)",
      "line": {"color": "#ef4444", "width": 2.5}
    },
    {
      "x": ["08:00", "10:00", "12:00", "14:00", "16:00"],
      "y": [420, 390, 360, 340, 310],
      "type": "scatter",
      "mode": "lines",
      "name": "Intake Pressure (PSI)",
      "yaxis": "y2",
      "line": {"color": "#3b82f6", "width": 2}
    }
  ],
  "layout": {
    "showlegend": true,
    "hovermode": "x unified",
    "xaxis": {"title": "Time (24-hour window)"},
    "yaxis": {"title": "Flow Rate (BPD)", "side": "left"},
    "yaxis2": {"title": "Pressure (PSI)", "side": "right", "overlaying": "y"}
  }
}
```

**Frontend renders:**

```tsx
<PlotlyChartBlock chartPayload={{
  chart_id: "chart-001",
  title: "24-Hour Production & Pressure Trend",
  data: [...],
  layout: {...}
}} />
```

**Result:** Interactive dual Y-axis chart with hover tooltips

---

### Example 3: Advisory Payload Event

**Backend sends:**
```json
{
  "type": "advisory",
  "run_id": "RUN-UI-a7b3f2e1",
  "advisory": {
    "advisory_id": "ADV-20260828-001",
    "asset_id": "FS-031",
    "objective_id": "OP02_PRODUCTION_DECLINE_RCA",
    "assessment": "Production rate declined from 1650 BPD to 1350 BPD over 6 hours due to gas interference.",
    "diagnosis": "Intake pressure dropped from 420 PSI to 310 PSI. Free gas entering pump intake reduces volumetric efficiency. BEP deviation increased to -18%.",
    "recommendation": "Reduce frequency from 60 Hz to 52 Hz. Monitor motor temperature for 6 hours. Verify wellhead backpressure sensor calibration.",
    "confidence": 0.87,
    "risk": "MEDIUM",
    "constraints": [
      "Do not exceed 3100 PSI discharge pressure",
      "Monitor motor temperature < 120°C",
      "Maintain intake pressure > 280 PSI"
    ],
    "verification": [
      "Verify wellhead backpressure sensor calibration",
      "Review 24-hour trend before frequency adjustment",
      "Confirm gas-oil ratio from latest well test"
    ],
    "evidence": [
      {
        "source_type": "TELEMETRY",
        "source_id": "TEL-FS031-20260828",
        "observation": "Intake pressure dropped from 420 PSI to 310 PSI",
        "timestamp": "2026-08-28T10:30:00Z"
      },
      {
        "source_type": "MODEL",
        "source_id": "ML-INFERENCE-20260828",
        "observation": "Gas interference fault predicted with 92% confidence",
        "timestamp": "2026-08-28T10:35:00Z"
      },
      {
        "source_type": "ENGINEERING",
        "source_id": "TDH-CALC-20260828",
        "observation": "BEP deviation increased to -18% (downthrust risk)",
        "timestamp": "2026-08-28T10:36:00Z"
      }
    ]
  }
}
```

**Frontend can extract:**
- **Primary action:** `recommendation`
- **Risk badge:** `risk` + `confidence`
- **Evidence count:** `evidence.length`
- **Safety constraints:** `constraints[]`
- **Verification steps:** `verification[]`

---

## 🎨 UI Component Mapping

### Markdown Block
**Triggers:** `event.type === "text_delta"`  
**Renders:** Formatted diagnostic text with headings, lists, bold

```tsx
{msg.textDelta && <MarkdownBlock content={msg.textDelta} />}
```

**Visual:**
```
┌──────────────────────────────────────────────────┐
│ ### 🛡️ Diagnostic Summary                       │
│                                                  │
│ **Assessment:** Production rate declined...      │
│                                                  │
│ **Diagnosis Details:** Root cause identified...  │
│                                                  │
│ #### 📊 Key Performance Indicators               │
│ - **Confidence Score:** 87%                      │
│ - **Risk Horizon:** MEDIUM                       │
└──────────────────────────────────────────────────┘
```

---

### Plotly Chart Block
**Triggers:** `event.type === "generative_ui" && event.kind === "plotly_chart"`  
**Renders:** Interactive chart with dual Y-axis, hover tooltips

```tsx
{msg.chart && <PlotlyChartBlock chartPayload={msg.chart} />}
```

**Visual:**
```
┌──────────────────────────────────────────────────┐
│ 📊 24-Hour Production & Pressure Trend           │
├──────────────────────────────────────────────────┤
│                                                  │
│   1700 BPD ┤       ●────●                        │
│            │      /      \                       │
│   1500 BPD ┤     /        ●───●                  │
│            │    /              \                 │
│   1300 BPD ┤   ●                ●────●  Flow     │
│            │                                     │
│    420 PSI ┤   ●                        Pressure │
│            │    \                                │
│    360 PSI ┤     ●──●                            │
│            │          \                          │
│    300 PSI ┤           ●────●───●                │
│            └─────┬─────┬─────┬─────┬───────▶    │
│                08:00  10:00 12:00 14:00  16:00  │
│                                                  │
│  [Interactive: Hover for exact values]          │
└──────────────────────────────────────────────────┘
```

---

### Status Banner Block
**Triggers:** `event.type === "status"`  
**Renders:** Animated loading indicator with stage name

```tsx
{msg.statusMessage && (
  <StatusBannerBlock 
    stage={msg.statusMessage.stage} 
    message={msg.statusMessage.text} 
  />
)}
```

**Visual:**
```
┌──────────────────────────────────────────────────┐
│ 🔄 [SPECIALISTS_RUNNING] Specialists evaluated   │
│    12 evidence items.                            │
└──────────────────────────────────────────────────┘
```

---

### Advisory Action Card Block
**Triggers:** `event.type === "advisory"` (parse recommendation)  
**Renders:** Color-coded recommendation with urgency badge

```tsx
<AdvisoryActionCardBlock
  title={advisory.recommendation}
  urgency={advisory.risk}
  confidence={advisory.confidence}
  onOpenEvidence={() => openEvidenceDrawer(runId)}
/>
```

**Visual (Medium Risk):**
```
┌──────────────────────────────────────────────────┐
│ 🛡️ Recommended Operator Action  [MEDIUM PRIORITY]│
│                                            (87%) │
├──────────────────────────────────────────────────┤
│ Reduce frequency from 60 Hz to 52 Hz. Monitor   │
│ motor temperature for 6 hours. Verify wellhead  │
│ backpressure sensor calibration.                 │
│                                                  │
│ View Full Evidence Audit Pack →                 │
└──────────────────────────────────────────────────┘
```

**Visual (High Risk):**
```
┌──────────────────────────────────────────────────┐
│ ⚠️ Recommended Operator Action    [HIGH PRIORITY]│
│                                            (92%) │
├──────────────────────────────────────────────────┤
│ URGENT: Shut down pump immediately. Motor temp   │
│ exceeded 130°C. Risk of thermal damage to stator.│
│                                                  │
│ View Full Evidence Audit Pack →                 │
└──────────────────────────────────────────────────┘
```

---

## 📦 Complete Event Sequence Example

**User Query:** "Why is production declining?"

**Full NDJSON Stream:**

```
{"type":"status","run_id":"RUN-UI-a7b3f2e1","stage":"INITIATING","message":"Routing query to OP02_PRODUCTION_DECLINE_RCA..."}

{"type":"status","run_id":"RUN-UI-a7b3f2e1","stage":"RESOLVING_ASSET","message":"Loading asset context for FS-031..."}

{"type":"status","run_id":"RUN-UI-a7b3f2e1","stage":"DATA_QUALITY_GATE","message":"Validating telemetry quality..."}

{"type":"status","run_id":"RUN-UI-a7b3f2e1","stage":"SPECIALISTS_RUNNING","message":"Engineering specialist calculating TDH & BEP..."}

{"type":"text_delta","delta":"### 🛡️ Diagnostic Summary for Asset `FS-031`\n\n"}

{"type":"text_delta","delta":"**Assessment:** Production rate declined from 1650 BPD to 1350 BPD over 6 hours.\n\n"}

{"type":"text_delta","delta":"**Diagnosis Details:** Root cause identified as gas interference. Intake pressure dropped from 420 PSI to 310 PSI, indicating free gas entering pump intake. This reduces volumetric efficiency and increases downthrust risk.\n\n"}

{"type":"text_delta","delta":"#### 📊 Key Performance Indicators\n"}
{"type":"text_delta","delta":"- **Confidence Score:** 87%\n"}
{"type":"text_delta","delta":"- **Risk Horizon:** `MEDIUM`\n"}
{"type":"text_delta","delta":"- **BEP Deviation:** -18% (downthrust regime)\n"}
{"type":"text_delta","delta":"- **TDH:** 4320 ft (target: 4800 ft)\n\n"}

{"type":"text_delta","delta":"#### 🔍 Supporting Evidence\n"}
{"type":"text_delta","delta":"- **Telemetry:** Intake pressure anomaly detected\n"}
{"type":"text_delta","delta":"- **Engineering:** TDH calculation confirms 18% deviation from BEP\n"}
{"type":"text_delta","delta":"- **ML Model:** Gas interference fault predicted with 92% confidence\n"}
{"type":"text_delta","delta":"- **Knowledge Base:** Historical case similarity (3 similar events in 2025)\n\n"}

{"type":"text_delta","delta":"#### ✅ Recommended Actions\n"}
{"type":"text_delta","delta":"1. **Immediate:** Reduce frequency from 60 Hz to 52 Hz\n"}
{"type":"text_delta","delta":"2. **Monitor:** Track motor temperature for next 6 hours (threshold < 120°C)\n"}
{"type":"text_delta","delta":"3. **Verification:** Confirm backpressure sensor calibration\n"}
{"type":"text_delta","delta":"4. **Follow-up:** Review gas-oil ratio from latest well test\n\n"}

{"type":"text_delta","delta":"#### ⚠️ Safety Constraints\n"}
{"type":"text_delta","delta":"- Do not exceed 3100 PSI discharge pressure\n"}
{"type":"text_delta","delta":"- Maintain intake pressure > 280 PSI\n"}
{"type":"text_delta","delta":"- Monitor motor temperature < 120°C\n\n"}

{"type":"advisory","run_id":"RUN-UI-a7b3f2e1","advisory":{...full payload...}}

{"type":"generative_ui","kind":"plotly_chart","run_id":"RUN-UI-a7b3f2e1","chart_id":"chart-001","title":"24-Hour Production & Pressure Trend","data":[...],"layout":{...}}

{"type":"done","run_id":"RUN-UI-a7b3f2e1"}
```

**Frontend Result:**

1. ✅ Loading banner shows 4 stages sequentially
2. ✅ Markdown streams word-by-word (typewriter effect)
3. ✅ Advisory payload stored for evidence drawer
4. ✅ Plotly chart renders below diagnostic text
5. ✅ Action card shows "MEDIUM PRIORITY (87%)" badge
6. ✅ "View Evidence" button links to drawer
7. ✅ Loading indicator disappears on `done` event

---

## 🧪 Testing Scenarios

### Test 1: Markdown Formatting
**Query:** "Diagnose faults on FS-031"

**Expected Markdown:**
```markdown
### 🛡️ Fault Diagnosis Summary

**Primary Fault:** Bearing Degradation

**Confidence:** 96%

#### Contributing Factors
- Motor temperature elevated to 125°C
- Vibration amplitude increased by 40%
- Drive current asymmetry detected

#### Recommended Action
Immediate workover required. Risk of catastrophic failure within 48 hours.
```

**NOT Expected:**
```
<h3>🛡️ Fault Diagnosis Summary</h3><p><strong>Primary Fault:</strong> Bearing Degradation</p>...
```

---

### Test 2: Plotly Chart Interactivity
**Query:** "Show me production trends"

**Expected:**
- Dual Y-axis chart (flow + pressure)
- Hover tooltips show exact values
- Legend toggles traces on/off
- Pan/zoom controls work
- Responsive on window resize

**NOT Expected:**
- Static image
- Single Y-axis only
- No hover tooltips
- Chart doesn't resize

---

### Test 3: Streaming Real-time
**Query:** "Why is production declining?"

**Expected:**
- Text appears word-by-word
- Status banners update sequentially
- Chart renders after text completes
- Total stream time: 3-5 seconds

**NOT Expected:**
- Blank screen for 5 seconds then full response
- Text appears all at once
- Loading indicator never clears

---

## 🎯 Quick Debugging

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Raw markdown symbols visible | ReactMarkdown not imported | Add `<ReactMarkdown>{content}</ReactMarkdown>` |
| Chart not rendering | Plotly not dynamically imported | Use `dynamic(() => import('react-plotly.js'), {ssr: false})` |
| Stream not updating | Event handler not calling setState | Verify `onEvent` callback updates React state |
| Evidence drawer empty | Wrong run_id passed | Check `run_id` from advisory event |
| Text appears all at once | Not parsing NDJSON line-by-line | Split on `\n` and parse each line separately |

---

## ✅ Final Checklist

Before deploying, verify:

- [ ] Markdown headings render as styled headers (not `### text`)
- [ ] Plotly charts are interactive (hover tooltips work)
- [ ] Text streams incrementally (typewriter effect)
- [ ] Status banners show and hide correctly
- [ ] Action cards display color-coded urgency
- [ ] Evidence drawer opens with structured data
- [ ] No raw JSON/HTML visible in UI
- [ ] No console errors during streaming
- [ ] Charts resize responsively
- [ ] Loading states clear on completion

---

**Backend is production-ready. Frontend components exist. Your job: wire them together beautifully. 🚀**
