'use client';

import React from 'react';
import { Activity, X } from 'lucide-react';

interface TopAppBarProps {
  assetId?: string;
  wellName?: string;
  statusText?: string;
  isAnalyzing?: boolean;
}

export default function TopAppBar({
  assetId = 'FS-031',
  wellName,
  statusText = 'Operational // Monitoring',
  isAnalyzing = false,
}: TopAppBarProps) {
  const displayContext = wellName || `Asset ID: ${assetId}`;

  return (
    <header className="w-full h-14 bg-[#f8f9fa] border-b border-[#e2e4e6] flex justify-between items-center px-4 md:px-6 flex-shrink-0 z-40">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-[#536600]/10 border border-[#536600]/30 flex items-center justify-center flex-shrink-0">
          <Activity className="w-4.5 h-4.5 text-[#536600]" />
        </div>
        <div>
          <h1 className="font-bold text-sm md:text-base text-[#191c1d] m-0 tracking-tight leading-none flex items-center gap-2">
            ESP APM // Enterprise Diagnostic Workspace
          </h1>
          <div className="font-mono text-[10px] md:text-[11px] text-[#666666] mt-1 flex items-center gap-2">
            <span>Context: {displayContext}</span>
            <span className="text-[#e2e4e6]">•</span>
            <span className="text-[#d4f658] bg-[#16181c] px-2 py-0.5 rounded-full inline-flex items-center gap-1.5 font-bold text-[10px]">
              <span
                className={`w-2 h-2 rounded-full bg-[#d4f658] ${
                  isAnalyzing ? 'animate-pulse' : ''
                }`}
              />
              {statusText}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        <button
          onClick={() => alert('Log exported to audit storage.')}
          className="font-mono text-xs font-semibold text-[#454936] hover:text-[#536600] hover:border-[#536600] transition-colors active:scale-95 px-3 md:px-4 py-1.5 border border-[#757964]/60 rounded-full bg-[#ffffff] shadow-sm"
        >
          Export Log
        </button>
        <button
          onClick={() => alert('Case saved to history.')}
          className="font-mono text-xs text-[#000000] bg-[#d4f658] hover:bg-[#cff053] transition-colors active:scale-95 px-3 md:px-4 py-1.5 rounded-full flex items-center gap-1.5 font-bold shadow-sm"
        >
          Close Case
          <X className="w-3.5 h-3.5 text-[#000000]" />
        </button>
      </div>
    </header>
  );
}
