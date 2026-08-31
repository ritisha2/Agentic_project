# ESP Agent Frontend-Backend Wiring Guide
## React Developer Handover Document

**Version:** 1.0  
**Date:** 2026-08-28  
**Target Audience:** React/Next.js Frontend Developers  
**Backend Stack:** Python FastAPI + LangGraph Supervisor  
**Frontend Stack:** Next.js 15 + TypeScript + React + Tailwind CSS + Plotly.js

---

## 🎯 Executive Summary

This document explains how the **ESP Agent backend** (running on `:8090`) sends diagnostic data to the **React frontend UI**, and how to properly render it with:

✅ **Formatted Markdown** (not HTML dumps)  
✅ **Interactive Plotly Charts** (time-series trends, pump curves)  
✅ **Real-time Streaming** (NDJSON Server-Sent Events)  
✅ **Evidence Cards** (Pydantic-validated structured data)  

**Current Status:** ✅ **Backend fully implemented and streaming correctly**  
**Your Task:** Ensure frontend renders all response types beautifully

---

## 📡 Backend API Architecture

### Base URLs
- **Production Gateway:** `http://127.0.0.1:8090` (agent + LangGraph)
- **Data Backend:** `http://127.0.0.1:8000` (cced_esp telemetry/ML)
- **Frontend Dev Server:** `http://localhost:3000`

### Environment Variables (`.env.local`)
```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8090
```

---

## 🔌 API Endpoints Reference

### 1. **Workspace Data (Asset Context + Telemetry)**
**Endpoint:** `GET /api/ui/assets/{asset_id}/workspace`

**Purpose:** Load initial asset state before user asks questions

**Response Schema:**
```typescript
interface AssetWorkspaceData {
  status: "SUCCESS";
  asset_id: string;  // e.g. "FS-031"
  
  asset_context: {
    asset_id: string;
    well_id: string;
    status: "ACTIVE" | "INACTIVE";
    pump_model?: string;        // e.g. "GC6100"
    motor_rating_hp?: number;   // e.g. 150
    be_point_bpd?: number;      // Best Efficiency Point (1650 BPD)
    installation_depth_ft?: number;
  };
  
  telemetry: {
    metrics: {
      motor_temperature: number;    // °C
      intake_pressure: number;      // PSI
      discharge_pressure: number;   // PSI
      flow_rate: number;            // BPD
      vibration_x: number;          // g-force
      drive_current_average: number; // Amps
      frequency: number;            // Hz
    };
    quality_status: "GOOD" | "DEGRADED" | "UNAVAILABLE";
    timestamp: string; // ISO 8601
  };
  
  engineering: {
    tdh_ft: number;             // Total Dynamic Head (feet)
    bep_deviation_pct: number;  // % deviation from BEP
  };
  
  predictive_models: {
    fault_classifier: {
      identified_fault: string;  // e.g. "Gas Interference"
      confidence: number;        // 0.0 - 1.0
    };
    risk_24h: {
      risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
      score: number;  // 0.0 - 1.0
    };
  };
  
  recent_pack_id?: string;  // Latest evidence pack ID for this asset
}
```

**Example Request:**
```typescript
const workspace = await fetch(`${API_BASE}/api/ui/assets/FS-031/workspace`)
  .then(res => res.json());
```

---

### 2. **Agent Query Streaming (Real-time Diagnostic)**
**Endpoint:** `POST /api/ui/agent/stream`

**Purpose:** User asks question → Agent streams response in real-time

**Request Body:**
```typescript
interface AgentStreamRequest {
  asset_id: string;   // e.g. "FS-031"
  user_query: string; // e.g. "Why is production declining?"
}
```

**Response Format:** NDJSON (Newline-Delimited JSON) stream

**Event Types:**

#### Event 1: Status Update
```json
{
  "type": "status",
  "run_id": "RUN-UI-a7b3f2e1",
  "stage": "INITIATING" | "SPECIALISTS_RUNNING" | "EVIDENCE_COLLECTED",
  "message": "Evaluating asset operational status..."
}
```

#### Event 2: Text Chunk (Markdown)
```json
{
  "type": "text_delta",
  "delta": "### 🛡️ Diagnostic Summary\n\n**Assessment:** Bearing degradation detected..."
}
```

#### Event 3: Advisory Payload (Full Structured Response)
```json
{
  "type": "advisory",
  "run_id": "RUN-UI-a7b3f2e1",
  "advisory": {
    "advisory_id": "ADV-20260828-001",
    "asset_id": "FS-031",
    "objective_id": "OP02_PRODUCTION_DECLINE_RCA",
    "assessment": "Production rate declined from 1650 BPD to 1350 BPD...",
    "diagnosis": "Root cause: Intake pressure drop suggests gas interference...",
    "recommendation": "Reduce frequency to 52 Hz and monitor for 6 hours.",
    "confidence": 0.87,
    "risk": "MEDIUM",
    "constraints": [
      "Do not exceed 3100 PSI discharge pressure",
      "Monitor motor temperature < 120°C"
    ],
    "verification": [
      "Verify wellhead backpressure sensor calibration",
      "Review 24-hour trend before frequency adjustment"
    ],
    "evidence": [
      {
        "source_type": "TELEMETRY",
        "source_id": "TEL-FS031-20260828",
        "observation": "Intake pressure dropped from 420 PSI to 310 PSI",
        "timestamp": "2026-08-28T10:30:00Z"
      }
    ]
  }
}
```

#### Event 4: Plotly Chart (Interactive Visualization)
```json
{
  "type": "generative_ui",
  "kind": "plotly_chart",
  "run_id": "RUN-UI-a7b3f2e1",
  "chart_id": "chart-20260828-001",
  "title": "Telemetry Trend & Pump Curve — Asset FS-031",
  "data": [
    {
      "x": ["10:00", "10:05", "10:10", "10:15", "10:20"],
      "y": [1650, 1580, 1520, 1450, 1350],
      "type": "scatter",
      "mode": "lines+markers",
      "name": "Production Rate (BPD)",
      "line": { "color": "#ef4444", "width": 2.5 }
    },
    {
      "x": ["10:00", "10:05", "10:10", "10:15", "10:20"],
      "y": [420, 390, 360, 340, 310],
      "type": "scatter",
      "mode": "lines",
      "name": "Intake Pressure (PSI)",
      "yaxis": "y2",
      "line": { "color": "#3b82f6", "width": 2 }
    }
  ],
  "layout": {
    "showlegend": true,
    "hovermode": "x unified",
    "xaxis": { "title": "Time (24-hour window)" },
    "yaxis": { "title": "Flow Rate (BPD)", "side": "left" },
    "yaxis2": {
      "title": "Pressure (PSI)",
      "side": "right",
      "overlaying": "y"
    }
  }
}
```

#### Event 5: Done
```json
{
  "type": "done",
  "run_id": "RUN-UI-a7b3f2e1"
}
```

---

### 3. **Evidence Pack Retrieval**
**Endpoint:** `GET /api/ui/runs/{run_id}/evidence`

**Purpose:** Fetch detailed evidence audit trail after agent completes

**Response Schema:**
```typescript
interface RunEvidenceData {
  run_id: string;
  evidence_pack: {
    pack_id: string;
    frozen: boolean;
    checksum?: string;
    items: Array<{
      evidence_id: string;
      evidence_type: "TELEMETRY" | "MODEL" | "ENGINEERING" | "KNOWLEDGE" | "CASE";
      source_system: string;
      source_id: string;
      authority_level: "A" | "B" | "C";
      quality_status: "GOOD" | "DEGRADED" | "UNAVAILABLE";
      statement: string;
      confidence: number;
    }>;
    conflicts: Array<{
      conflict_id: string;
      conflict_type: "VALUE_MISMATCH" | "AUTHORITY_DISPUTE";
      authority_comparison: string;
      resolution_method?: string;
    }>;
  };
  xai_explanation: {
    primary_diagnosis: string;
    confidence: number;
    supporting_evidence_count: number;
    conflicting_evidence_count: number;
    source_contributions: Record<string, number>;
    counterfactuals: string[];
  };
}
```

---

## 🎨 Frontend Implementation Guide

### Current UI Structure

```
esp_agent/ui/src/
├── app/
│   └── page.tsx                    # Root: redirects to /workspace/FS-031
├── components/
│   ├── dialog/
│   │   ├── AgentDialog.tsx         # Main chat interface
│   │   └── GenerativeUIBlocks.tsx  # Markdown, Plotly, Status renderers
│   ├── evidence/
│   │   └── EvidenceDrawer.tsx      # Evidence pack viewer (side drawer)
│   └── workspace/
│       ├── MessageComposer.tsx     # User input field
│       └── TopAppBar.tsx           # Asset selector header
└── lib/
    └── api.ts                      # Typed API client functions
```

---

### ✅ Already Implemented Components

#### 1. **MarkdownBlock** (Markdown Renderer)
**File:** `src/components/dialog/GenerativeUIBlocks.tsx`

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none text-[#191c1d] leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

**What it handles:**
- ✅ Headings (`### Diagnostic Summary`)
- ✅ Bold/Italic (`**Assessment:**`)
- ✅ Lists (bullet points, numbered)
- ✅ Code blocks (`` `asset_id` ``)
- ✅ Tables (via `remarkGfm`)
- ✅ Links (`[documentation](https://...`)

**Current Status:** ✅ **Working perfectly** — no HTML dump issues

---

#### 2. **PlotlyChartBlock** (Interactive Charts)
**File:** `src/components/dialog/GenerativeUIBlocks.tsx`

```tsx
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <div>Loading chart...</div>
});

export function PlotlyChartBlock({ chartPayload }: { chartPayload: PlotlyChartData }) {
  return (
    <div className="my-4 p-3 bg-white border rounded-2xl">
      <h4 className="text-xs font-semibold mb-2">
        {chartPayload.title || 'Interactive Chart'}
      </h4>
      <div className="w-full h-72">
        <Plot
          data={chartPayload.data}
          layout={{
            ...chartPayload.layout,
            responsive: true,
            autosize: true,
            margin: { l: 45, r: 45, t: 20, b: 35 }
          }}
          useResizeHandler={true}
          className="w-full h-full"
          config={{ displayModeBar: true, responsive: true }}
        />
      </div>
    </div>
  );
}
```

**What it handles:**
- ✅ Dual Y-axis charts (flow + pressure)
- ✅ Time-series trends (24-hour window)
- ✅ Hover tooltips (`hovermode: 'x unified'`)
- ✅ Interactive pan/zoom
- ✅ Responsive resizing

**Current Status:** ✅ **Fully functional** — backend streams correct Plotly JSON

---

#### 3. **StatusBannerBlock** (Loading/Progress Indicators)
**File:** `src/components/dialog/GenerativeUIBlocks.tsx`

```tsx
export function StatusBannerBlock({ stage, message }: { stage: string; message: string }) {
  return (
    <div className="my-2 p-2.5 bg-sky-50 border border-sky-200 rounded-xl flex items-center gap-2.5">
      <Activity className="w-4 h-4 text-sky-600 animate-spin" />
      <span className="font-mono text-xs">[{stage}]</span>
      <span className="text-xs">{message}</span>
    </div>
  );
}
```

**What it handles:**
- ✅ Real-time stage updates (INITIATING → SPECIALISTS_RUNNING → DONE)
- ✅ Animated spinner during processing
- ✅ Auto-dismisses when stream completes

**Current Status:** ✅ **Working**

---

#### 4. **AdvisoryActionCardBlock** (Recommendation Cards)
**File:** `src/components/dialog/GenerativeUIBlocks.tsx`

```tsx
export function AdvisoryActionCardBlock({
  title,
  urgency,
  confidence,
  onOpenEvidence,
}: {
  title: string;
  urgency: string;
  confidence: number;
  onOpenEvidence?: () => void;
}) {
  const isHigh = urgency.toLowerCase() === 'high' || urgency.toLowerCase() === 'critical';

  return (
    <div className={`my-3 p-4 rounded-2xl border ${
      isHigh ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'
    }`}>
      <div className="flex items-center justify-between">
        {isHigh ? <ShieldAlert /> : <CheckCircle2 />}
        <span className="text-xs font-bold">Recommended Operator Action</span>
        <span className="text-xs font-mono">
          {urgency.toUpperCase()} PRIORITY ({Math.round(confidence * 100)}%)
        </span>
      </div>
      <p className="text-sm font-semibold mt-2">{title}</p>
      {onOpenEvidence && (
        <button onClick={onOpenEvidence} className="text-xs text-sky-700 mt-2">
          View Full Evidence Audit Pack →
        </button>
      )}
    </div>
  );
}
```

**Current Status:** ✅ **Implemented** — shows high/low urgency with color coding

---

### 🔄 Streaming Implementation (NDJSON Parser)

**File:** `src/lib/api.ts`

```typescript
export async function runAgentStreamQuery(
  assetId: string,
  userQuery: string,
  onEvent: (event: any) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/ui/agent/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_id: assetId, user_query: userQuery }),
  });

  if (!res.ok || !res.body) {
    throw new Error('Streaming agent request failed');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';  // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.trim()) {
        try {
          const parsed = JSON.parse(line);
          onEvent(parsed);  // Trigger React state update
        } catch (e) {
          console.error('Failed to parse NDJSON line:', line, e);
        }
      }
    }
  }

  // Handle any remaining buffered content
  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer));
    } catch (e) {}
  }
}
```

**How it works:**
1. Opens HTTP stream to `/api/ui/agent/stream`
2. Reads NDJSON line-by-line (one JSON object per line)
3. Parses each line into event object
4. Calls `onEvent()` callback → React updates UI in real-time
5. Backend yields events as they're generated (no buffering delay)

**Current Status:** ✅ **Working perfectly**

---

### 📊 Event Handling in AgentDialog

**File:** `src/components/dialog/AgentDialog.tsx`

```typescript
await runAgentStreamQuery(assetId, queryText, (event) => {
  setMessages((prev) =>
    prev.map((msg) => {
      if (msg.id !== agentMsgId) return msg;

      if (event.type === 'status') {
        return {
          ...msg,
          statusMessage: { stage: event.stage, text: event.message }
        };
      } 
      else if (event.type === 'text_delta') {
        return {
          ...msg,
          textDelta: (msg.textDelta || '') + event.delta  // Append chunk
        };
      } 
      else if (event.type === 'advisory') {
        return {
          ...msg,
          advisory: event.advisory  // Store full advisory
        };
      } 
      else if (event.type === 'generative_ui' && event.kind === 'plotly_chart') {
        return {
          ...msg,
          chart: event  // Store chart data
        };
      } 
      else if (event.type === 'done') {
        return {
          ...msg,
          statusMessage: undefined  // Clear loading indicator
        };
      }
      return msg;
    })
  );
});
```

**What happens:**
- `status` event → Shows animated loading banner
- `text_delta` event → Appends text to markdown block (streaming typewriter effect)
- `advisory` event → Stores full advisory payload (can show in card)
- `generative_ui` event → Renders Plotly chart below markdown
- `done` event → Hides loading indicator, marks stream complete

**Current Status:** ✅ **Fully implemented**

---

## 🚀 What's Already Working

| Component | Status | Notes |
|-----------|--------|-------|
| Markdown Rendering | ✅ Done | ReactMarkdown + remarkGfm |
| Plotly Charts | ✅ Done | Dual Y-axis, time-series, interactive |
| NDJSON Streaming | ✅ Done | Real-time event parsing |
| Status Banners | ✅ Done | Animated progress indicators |
| Action Cards | ✅ Done | Color-coded urgency + confidence |
| Evidence Drawer | ✅ Done | Side panel for audit trail |
| Agent Dialog | ✅ Done | Full chat interface with streaming |

**⚠️ You should NOT see:**
- Raw HTML dumps (`<div>...</div>` in chat)
- Unstyled JSON blobs
- Broken chart renders
- Missing markdown formatting

**If you do see these**, the backend response is correct — check your frontend rendering logic.

---

## 🎯 Your Tasks (React Developer)

### ✅ Verification Checklist

1. **Test Markdown Rendering**
   - Open agent dialog
   - Ask: *"Why is production declining on FS-031?"*
   - **Expected:** Formatted headings, bullet points, bold text
   - **NOT:** Raw markdown symbols (`###`, `**`)

2. **Test Plotly Charts**
   - Check that interactive chart renders below diagnostic text
   - **Expected:** Dual Y-axis with hover tooltips
   - **NOT:** Loading spinner that never resolves

3. **Test Streaming**
   - Watch text appear word-by-word (not all at once)
   - **Expected:** Typewriter effect as backend yields chunks
   - **NOT:** Blank screen then sudden full response

4. **Test Evidence Drawer**
   - Click "View Full Evidence Audit Pack" link
   - **Expected:** Side drawer slides in with evidence items
   - **NOT:** 404 error or blank drawer

5. **Test Status Updates**
   - Watch for `[INITIATING]` → `[SPECIALISTS_RUNNING]` banners
   - **Expected:** Animated spinner with stage names
   - **NOT:** Static text or missing updates

---

### 🐛 Debugging Tips

#### Problem: Markdown not rendering (seeing raw `### text`)
**Solution:** Verify `ReactMarkdown` is imported and `remarkGfm` plugin is loaded

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

<ReactMarkdown remarkPlugins={[remarkGfm]}>
  {content}
</ReactMarkdown>
```

#### Problem: Plotly chart not showing
**Solution:** Check console for errors. Plotly must be dynamically imported:

```tsx
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });
```

#### Problem: Stream not updating in real-time
**Solution:** Verify `onEvent` callback is calling `setMessages` correctly:

```tsx
onEvent={(event) => {
  setMessages((prev) => /* update logic */);
}}
```

#### Problem: Evidence drawer empty
**Solution:** Check `run_id` is passed correctly to `/api/ui/runs/{run_id}/evidence`

---

## 📦 NPM Dependencies Required

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "next": "^15.0.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "react-plotly.js": "^2.6.0",
    "plotly.js": "^2.32.0",
    "lucide-react": "^0.400.0"
  }
}
```

Install:
```bash
cd esp_agent/ui
npm install react-markdown remark-gfm react-plotly.js plotly.js lucide-react
```

---

## 🔍 Backend Response Examples (Real Data)

### Example 1: Production Decline Query

**User asks:** *"Why is production declining on FS-031?"*

**Backend streams:**

```
{"type":"status","run_id":"RUN-UI-a7b3f2e1","stage":"INITIATING","message":"Evaluating asset operational status..."}
{"type":"status","run_id":"RUN-UI-a7b3f2e1","stage":"SPECIALISTS_RUNNING","message":"Specialists evaluated 12 evidence items."}
{"type":"text_delta","delta":"### 🛡️ Diagnostic Summary for Asset `FS-031`\n\n"}
{"type":"text_delta","delta":"**Assessment:** Production rate declined from 1650 BPD to 1350 BPD over 6 hours.\n\n"}
{"type":"text_delta","delta":"**Diagnosis Details:** Root cause identified as gas interference. Intake pressure dropped from 420 PSI to 310 PSI, indicating free gas entering pump intake.\n\n"}
{"type":"text_delta","delta":"#### 📊 Key Performance Indicators\n- **Confidence Score:** 87%\n- **Risk Horizon:** `MEDIUM`\n\n"}
{"type":"text_delta","delta":"#### 🔍 Supporting Evidence\n- Telemetry: Intake pressure anomaly detected\n- Engineering: TDH calculation confirms 18% deviation from BEP\n- ML Model: Gas interference fault predicted with 92% confidence\n\n"}
{"type":"text_delta","delta":"#### ✅ Recommended Actions\n1. **Immediate:** Reduce frequency from 60 Hz to 52 Hz\n2. **Monitor:** Track motor temperature for next 6 hours\n3. **Verification:** Confirm backpressure sensor calibration\n\n"}
{"type":"advisory","run_id":"RUN-UI-a7b3f2e1","advisory":{...full advisory payload...}}
{"type":"generative_ui","kind":"plotly_chart","run_id":"RUN-UI-a7b3f2e1","data":[...plotly chart data...]}
{"type":"done","run_id":"RUN-UI-a7b3f2e1"}
```

**Frontend renders:**
- ✅ Formatted markdown with headings and bullets
- ✅ Interactive Plotly chart showing 24-hour trend
- ✅ Action card with "MEDIUM PRIORITY" badge
- ✅ Link to evidence drawer

---

### Example 2: Fault Diagnosis Query

**User asks:** *"Diagnose faults on FS-031"*

**Backend routes to:** `OP03_FAULT_DIAGNOSIS`

**Response includes:**
- Markdown diagnostic summary
- Fault classification (e.g. "Bearing Degradation")
- Confidence score (0.96)
- Plotly chart: Motor temperature trend
- Evidence pack with 8 items (telemetry + ML model + knowledge base)

---

## 📚 Additional Resources

### Backend Source Files
- **Streaming endpoint:** `src/api/rest/bff_routes.py` (line 186)
- **Workspace endpoint:** `src/api/rest/bff_routes.py` (line 68)
- **Evidence endpoint:** `src/api/rest/evidence_routes.py`
- **Supervisor graph:** `src/agent/supervisor/graph_builder.py`

### Frontend Source Files
- **API client:** `src/lib/api.ts`
- **Agent dialog:** `src/components/dialog/AgentDialog.tsx`
- **UI blocks:** `src/components/dialog/GenerativeUIBlocks.tsx`
- **Evidence drawer:** `src/components/evidence/EvidenceDrawer.tsx`

### Testing
1. **Start backend:**
   ```bash
   cd esp_agent
   python run_agent_server.py
   ```

2. **Start frontend:**
   ```bash
   cd esp_agent/ui
   npm run dev
   ```

3. **Open browser:**
   ```
   http://localhost:3000/workspace/FS-031
   ```

4. **Test queries:**
   - "Why is production declining?"
   - "Diagnose faults on this asset"
   - "Show me the health assessment"
   - "List all fleet assets" (fleet-tier query)

---

## ✅ Acceptance Criteria

Before marking this task complete, verify:

- [ ] Markdown renders with proper headings, bullets, bold text
- [ ] Plotly charts are interactive (hover tooltips work)
- [ ] Text streams word-by-word (not all at once)
- [ ] Status banners show stage progression
- [ ] Action cards display urgency + confidence correctly
- [ ] Evidence drawer opens and shows structured evidence
- [ ] No raw HTML or JSON dumps visible in chat
- [ ] No console errors during streaming
- [ ] Charts are responsive on window resize
- [ ] Loading states clear when stream completes

---

## 🆘 Support

**If you encounter issues:**

1. Check browser console for errors
2. Verify backend is running on `:8090` (`curl http://localhost:8090/api/ui/health`)
3. Check network tab to see raw NDJSON stream
4. Compare actual event types against this doc
5. Verify NPM dependencies are installed
6. Check that `NEXT_PUBLIC_API_BASE` env var is set

**Backend is streaming correctly** — if UI looks broken, it's a frontend rendering issue.

---

## 🎓 Key Takeaways

1. **Backend streams NDJSON events** — one JSON object per line
2. **Frontend parses line-by-line** — updates React state for each event
3. **Markdown is pre-formatted by backend** — no HTML sanitization needed
4. **Plotly JSON is ready-to-render** — just pass `data` and `layout` props
5. **Evidence is Pydantic-validated** — strict schema, no surprises
6. **All responses are typed** — TypeScript interfaces match backend contracts

**You have everything you need** — backend is production-ready, frontend components exist, streaming works. Your job is to ensure all pieces render beautifully together. 🚀
