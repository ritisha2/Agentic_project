/**
 * Strongly-typed API client for ESP APM FastAPI BFF Gateway
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export interface AssetWorkspaceData {
  status: string;
  asset_id: string;
  asset_context: {
    asset_id: string;
    well_id: string;
    status: string;
    pump_model?: string;
    motor_rating_hp?: number;
    be_point_bpd?: number;
    installation_depth_ft?: number;
  };
  telemetry: {
    metrics: Record<string, number>;
    quality_status: string;
    timestamp: string;
  };
  engineering: {
    tdh_ft: number;
    bep_deviation_pct: number;
  };
  predictive_models: {
    fault_classifier: { identified_fault: string; confidence: number };
    risk_24h: { risk_level: string; score: number };
  };
  recent_pack_id?: string;
}

export interface AgentRunResponse {
  run_id: string;
  status: string;
  objective_id: string;
  advisory: {
    advisory_id: string;
    asset_id: string;
    objective_id: string;
    assessment: string;
    diagnosis: string;
    confidence: number;
    risk: string;
    recommendation: string;
    constraints: string[];
    verification: string[];
    evidence: Array<{
      source_type: string;
      source_id: string;
      observation: string;
      timestamp: string;
    }>;
  };
}

export interface RunEvidenceData {
  run_id: string;
  evidence_pack: {
    pack_id: string;
    frozen: boolean;
    checksum?: string;
    items: Array<{
      evidence_id: string;
      evidence_type: string;
      source_system: string;
      source_id: string;
      authority_level: string;
      quality_status: string;
      statement: string;
      confidence: number;
    }>;
    conflicts: Array<{
      conflict_id: string;
      conflict_type: string;
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
    visual_stories: Array<{
      story_id: string;
      story_type: string;
      title: string;
      description: string;
      series: any[];
      annotations: any[];
    }>;
  };
}

export async function fetchAssetWorkspace(assetId: string): Promise<AssetWorkspaceData> {
  const res = await fetch(`${API_BASE}/api/ui/assets/${assetId}/workspace`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to fetch workspace for ${assetId}`);
  return res.json();
}

export async function runAgentQuery(assetId: string, userQuery: string): Promise<AgentRunResponse> {
  const res = await fetch(`${API_BASE}/api/ui/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_id: assetId, user_query: userQuery }),
  });
  if (!res.ok) throw new Error('Agent run request failed');
  return res.json();
}

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
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.trim()) {
        try {
          const parsed = JSON.parse(line);
          onEvent(parsed);
        } catch (e) {
          console.error('Failed to parse NDJSON line:', line, e);
        }
      }
    }
  }

  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer));
    } catch (e) {}
  }
}

export async function fetchRunEvidence(runId: string): Promise<RunEvidenceData> {
  const res = await fetch(`${API_BASE}/api/ui/runs/${runId}/evidence`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to fetch evidence for ${runId}`);
  return res.json();
}

