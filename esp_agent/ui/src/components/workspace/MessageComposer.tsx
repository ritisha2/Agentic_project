'use client';

import React, { useState } from 'react';
import { Paperclip, Terminal, Send } from 'lucide-react';

interface MessageComposerProps {
  onSendMessage: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export default function MessageComposer({
  onSendMessage,
  isLoading = false,
  placeholder = 'Ask Jane about telemetry, diagnostics...',
}: MessageComposerProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSendMessage(query.trim());
    setQuery('');
  };

  return (
    <div className="w-full bg-[#ffffff] pt-2">
      <form
        onSubmit={handleSubmit}
        className="w-full flex items-center bg-[#f8f9fa] border border-[#e2e4e6] rounded-full shadow-sm focus-within:border-[#536600] focus-within:ring-1 focus-within:ring-[#536600] transition-all p-1"
      >
        <button
          type="button"
          aria-label="Attach File"
          className="w-8 h-8 flex items-center justify-center rounded-full text-[#666666] hover:bg-[#e1e3e4] transition-colors flex-shrink-0"
        >
          <Paperclip className="w-3.5 h-3.5 text-[#666666]" />
        </button>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isLoading}
          placeholder={placeholder}
          className="flex-1 min-w-0 bg-transparent border-none focus:outline-none focus:ring-0 text-xs text-[#191c1d] px-2 py-1.5 placeholder-[#666666] font-sans"
        />

        <div className="flex items-center gap-1 flex-shrink-0 pr-0.5">
          <button
            type="button"
            aria-label="Command Mode"
            className="w-8 h-8 flex items-center justify-center rounded-full text-[#666666] hover:bg-[#e1e3e4] transition-colors"
          >
            <Terminal className="w-3.5 h-3.5 text-[#666666]" />
          </button>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            aria-label="Send Message"
            className="w-8 h-8 flex items-center justify-center rounded-full bg-[#16181c] text-[#d4f658] hover:bg-[#000000] transition-colors disabled:opacity-30 shadow-sm"
          >
            {isLoading ? (
              <span className="w-3.5 h-3.5 rounded-full border-2 border-[#d4f658] border-t-transparent animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5 text-[#d4f658]" />
            )}
          </button>
        </div>
      </form>

      <div className="mt-1.5 text-center">
        <p className="font-mono text-[9px] text-[#666666] leading-none">
          Agent Jane analyzes telemetry. Verify physical actions before execution.
        </p>
      </div>
    </div>
  );
}
