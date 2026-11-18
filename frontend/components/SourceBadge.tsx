'use client';

import React from 'react';

export interface SourceData {
  title: string;
  url: string;
  platform: 'darglobal' | 'wasalt' | string;
  scraped_at?: string;
}

export default function SourceBadge({ source }: { source: SourceData }) {
  const isDg = source.platform === 'darglobal';

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-slate-800/80 hover:bg-slate-700 border border-slate-700/80 hover:border-sky-400 text-slate-300 hover:text-white transition group"
      title={`Source: ${source.title} (${source.scraped_at ? 'Scraped ' + source.scraped_at : ''})`}
    >
      <span className={`w-2 h-2 rounded-full ${isDg ? 'bg-amber-400' : 'bg-sky-400'}`} />
      <span className="font-medium text-[11px] text-slate-400 uppercase tracking-wider">
        {isDg ? 'DarGlobal' : 'Wasalt'}:
      </span>
      <span className="max-w-[200px] truncate">{source.title}</span>
      <svg className="w-3 h-3 text-slate-500 group-hover:text-sky-400 transition" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
      </svg>
    </a>
  );
}
