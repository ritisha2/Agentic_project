'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Activity, ShieldAlert, CheckCircle2, ChevronRight } from 'lucide-react';

// Dynamic lazy import of react-plotly.js to avoid SSR issues & heavy initial bundles
const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-64 w-full flex items-center justify-center bg-gray-50 border border-gray-200 rounded-xl animate-pulse text-xs text-gray-500">
      <Activity className="w-5 h-5 animate-spin mr-2 text-sky-600" /> Rendering Interactive Engineering Chart...
    </div>
  ),
});

export interface PlotlyChartData {
  chart_id: string;
  title: string;
  data: any[];
  layout: any;
}

export function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none text-[#191c1d] dark:text-gray-100 leading-relaxed font-sans prose-headings:font-semibold prose-headings:text-[#001f2a] prose-a:text-sky-600 prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}

export function PlotlyChartBlock({ chartPayload }: { chartPayload: PlotlyChartData }) {
  return (
    <div className="my-4 p-3 bg-white border border-gray-200/80 rounded-2xl shadow-xs overflow-hidden">
      <div className="flex items-center justify-between mb-2 pb-2 border-b border-gray-100 px-1">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-600" />
          <h4 className="text-xs font-semibold text-gray-800 uppercase tracking-wider">
            {chartPayload.title || 'Generative Plotly Chart'}
          </h4>
        </div>
        <span className="text-[10px] bg-sky-50 text-sky-700 px-2 py-0.5 rounded-full border border-sky-200/60 font-mono">
          Interactive Plotly
        </span>
      </div>
      <div className="w-full h-72">
        <Plot
          data={chartPayload.data}
          layout={{
            ...chartPayload.layout,
            responsive: true,
            autosize: true,
            margin: { l: 45, r: 45, t: 20, b: 35 },
          }}
          useResizeHandler={true}
          className="w-full h-full"
          config={{ displayModeBar: true, responsive: true }}
        />
      </div>
    </div>
  );
}

export function StatusBannerBlock({ stage, message }: { stage: string; message: string }) {
  return (
    <div className="my-2 p-2.5 bg-sky-50/60 border border-sky-200/70 rounded-xl flex items-center gap-2.5 text-xs text-sky-900">
      <Activity className="w-4 h-4 text-sky-600 animate-spin shrink-0" />
      <div className="flex-1">
        <span className="font-mono font-semibold text-[10px] tracking-wider text-sky-700 uppercase mr-2">
          [{stage}]
        </span>
        <span>{message}</span>
      </div>
    </div>
  );
}

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
    <div
      className={`my-3 p-4 rounded-2xl border ${
        isHigh ? 'bg-amber-50/50 border-amber-200/80' : 'bg-emerald-50/50 border-emerald-200/80'
      } shadow-xs flex flex-col gap-2`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isHigh ? (
            <ShieldAlert className="w-5 h-5 text-amber-600" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          )}
          <span className="text-xs font-bold text-gray-900">Recommended Operator Action</span>
        </div>
        <span
          className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ${
            isHigh ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
          }`}
        >
          {urgency.toUpperCase()} PRIORITY ({Math.round(confidence * 100)}%)
        </span>
      </div>

      <p className="text-sm font-semibold text-gray-800 leading-snug">{title}</p>

      {onOpenEvidence && (
        <button
          onClick={onOpenEvidence}
          className="mt-1 self-start inline-flex items-center gap-1 text-xs font-semibold text-sky-700 hover:text-sky-900 transition-colors"
        >
          View Full Evidence Audit Pack <ChevronRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
