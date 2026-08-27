'use client';

import React from 'react';
import { RunEvidenceData } from '@/lib/api';

interface EvidenceDrawerProps {
  data: RunEvidenceData | null;
  onClose: () => void;
}

export default function EvidenceDrawer({ data, onClose }: EvidenceDrawerProps) {
  if (!data) return null;

  const { evidence_pack, xai_explanation } = data;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-[#16181c] border-l border-[#2a2d36] shadow-2xl z-50 overflow-y-auto p-6 text-[#f0f1f2]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#2a2d36] pb-4 mb-6">
        <div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#536600] text-[#d4f658]">
            {evidence_pack.frozen ? 'FROZEN SNAPSHOT' : 'LIVE'}
          </span>
          <h2 className="text-xl font-bold mt-1 text-white">Evidence Pack & XAI Trace</h2>
          <p className="text-xs font-mono text-[#9ea3b0]">Pack ID: {evidence_pack.pack_id}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-[#2a2d36] rounded-lg text-[#9ea3b0] hover:text-white font-mono text-sm"
        >
          ✕ Close
        </button>
      </div>

      {/* Checksum Verification */}
      {evidence_pack.checksum && (
        <div className="p-3 bg-[#1c1e24] border border-[#2a2d36] rounded-lg mb-6 text-xs font-mono text-[#d4f658]">
          SHA-256 Checksum: {evidence_pack.checksum}
        </div>
      )}

      {/* XAI 4-Part Summary */}
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-bold uppercase text-[#d4f658] mb-2 font-mono">
            1. Source Contributions (§3.1 Authority Precedence)
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(xai_explanation.source_contributions).map(([src, pct]) => (
              <div key={src} className="p-2 bg-[#1c1e24] border border-[#2a2d36] rounded text-xs font-mono flex justify-between">
                <span className="text-[#9ea3b0]">{src}</span>
                <span className="text-[#d4f658]">{pct}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Counterfactuals */}
        <div>
          <h3 className="text-sm font-bold uppercase text-[#e59819] mb-2 font-mono">
            2. What Would Change the Conclusion?
          </h3>
          <ul className="list-disc list-inside text-xs text-[#9ea3b0] space-y-1 font-mono">
            {xai_explanation.counterfactuals.map((cf, i) => (
              <li key={i}>{cf}</li>
            ))}
          </ul>
        </div>

        {/* Surfaced Conflicts */}
        {evidence_pack.conflicts.length > 0 && (
          <div>
            <h3 className="text-sm font-bold uppercase text-[#ba1a1a] mb-2 font-mono">
              3. Surfaced Evidence Conflicts ({evidence_pack.conflicts.length})
            </h3>
            {evidence_pack.conflicts.map((c) => (
              <div key={c.conflict_id} className="p-3 bg-[#1c1e24] border border-[#ba1a1a] rounded-lg text-xs font-mono mb-2">
                <div className="text-[#ba1a1a] font-bold">{c.conflict_type}</div>
                <div className="text-[#9ea3b0] mt-1">{c.authority_comparison}</div>
              </div>
            ))}
          </div>
        )}

        {/* Canonical Evidence Items */}
        <div>
          <h3 className="text-sm font-bold uppercase text-[#d4f658] mb-2 font-mono">
            4. Canonical Evidence Items ({evidence_pack.items.length})
          </h3>
          <div className="space-y-3">
            {evidence_pack.items.map((item) => (
              <div key={item.evidence_id} className="p-3 bg-[#1c1e24] border border-[#2a2d36] rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-bold text-[#d4f658]">{item.source_system} / {item.source_id}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#2a2d36] text-[#9ea3b0]">
                    {item.authority_level}
                  </span>
                </div>
                <p className="text-xs text-[#f0f1f2]">{item.statement}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
