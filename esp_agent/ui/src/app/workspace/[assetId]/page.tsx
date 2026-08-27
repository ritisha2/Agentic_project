'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import {
  fetchAssetWorkspace,
  fetchRunEvidence,
  AssetWorkspaceData,
  RunEvidenceData,
} from '@/lib/api';
import TopAppBar from '@/components/workspace/TopAppBar';
import AgentDialog from '@/components/dialog/AgentDialog';
import EvidenceDrawer from '@/components/evidence/EvidenceDrawer';
import { LayoutDashboard, Sparkles } from 'lucide-react';

export default function AssetWorkspacePage() {
  const params = useParams();
  const assetId = (params?.assetId as string) || 'FS-031';

  const [workspace, setWorkspace] = useState<AssetWorkspaceData | null>(null);
  const [evidenceData, setEvidenceData] = useState<RunEvidenceData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  useEffect(() => {
    fetchAssetWorkspace(assetId)
      .then(setWorkspace)
      .catch((err) => {
        console.warn('Backend workspace fetch notice (using client projection):', err);
      });
  }, [assetId]);

  const handleOpenEvidence = async (runId: string) => {
    try {
      const evData = await fetchRunEvidence(runId);
      setEvidenceData(evData);
      setIsDrawerOpen(true);
    } catch (err) {
      console.error('Failed to load evidence drawer data:', err);
    }
  };

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-[#f8f9fa] text-[#191c1d] dot-grid-bg relative select-none">
      {/* TopAppBar Header */}
      <TopAppBar
        assetId={assetId}
        statusText="Workspace Host // Main Dashboard Reserved"
        isAnalyzing={false}
      />

      {/* Main Workspace Canvas (Permanently Reserved for Main Dashboard) */}
      <main className="flex-1 w-full h-full relative flex items-center justify-center p-8">
        <div className="text-center max-w-md space-y-4 bg-white/70 backdrop-blur-md p-8 rounded-3xl border border-gray-200/80 shadow-xs">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-sky-50 text-sky-700 flex items-center justify-center border border-sky-200/60 shadow-xs">
            <LayoutDashboard className="w-7 h-7" />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-sm font-bold text-[#001f2a] tracking-wide uppercase font-mono">
              Main Dashboard Canvas Surface
            </h2>
            <p className="text-xs text-gray-500 leading-relaxed font-sans">
              This space is intentionally kept clean for the main APM asset dashboard. All AI agent actions, charts, and recommendations stream dynamically inside the Agent Jane dialog box.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded-full border border-emerald-200/60 text-[11px] font-medium font-mono">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
            <span>Agent Jane Generative UI Connected</span>
          </div>
        </div>

        {/* Dynamic Expandable Generative UI Agent Dialog Box */}
        <AgentDialog assetId={assetId} onOpenEvidenceDrawer={handleOpenEvidence} />
      </main>

      {/* Evidence Drawer */}
      {isDrawerOpen && (
        <EvidenceDrawer data={evidenceData} onClose={() => setIsDrawerOpen(false)} />
      )}
    </div>
  );
}
