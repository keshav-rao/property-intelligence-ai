'use client';

import React, { FormEvent, useEffect, useState, useRef } from 'react';
import PropertyCard, { PropertyData } from '../components/PropertyCard';
import CompareModal from '../components/CompareModal';
import SourceBadge, { SourceData } from '../components/SourceBadge';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceData[];
  properties?: PropertyData[];
  destinations?: { label: string; url: string; platform: string; description?: string }[];
}

interface StatsData {
  total_properties: number;
  darglobal_projects: number;
  wasalt_listings: number;
  cities_covered: number;
  model?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const STARTER_PROMPTS = [
  'What residential projects are listed by DarGlobal in Riyadh?',
  'What properties are available in Riyadh on Wasalt?',
  'Compare DarGlobal vs Wasalt: key differences, business models, and properties',
  'Which projects offer luxury residential facilities and branded designs?',
  'Show me apartments for rent in Jeddah under 40,000 SAR',
  'Tell me about the $234.6M Mouawad luxury residential project in Riyadh',
  'What branded residences are available in Dubai with Pagani or Missoni?'
];

export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: 'assistant',
      content:
        'Welcome to **Property Intelligence AI**. I am your real estate intelligence concierge trained on verified public records from **DarGlobal** and **Wasalt**.\n\n' +
        'You can ask me to discover luxury branded developments, search Saudi marketplace listings, compare properties side-by-side, or verify pricing and amenities.'
    }
  ]);

  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [stats, setStats] = useState<StatsData | null>(null);

  // Filters
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [cityFilter, setCityFilter] = useState<string>('all');
  const [purposeFilter, setPurposeFilter] = useState<string>('all');

  // Selected for comparison
  const [selectedProperties, setSelectedProperties] = useState<PropertyData[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Fetch stats on load
  useEffect(() => {
    fetch(`${API_BASE}/api/stats`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setStats(data);
      })
      .catch(() => {});
  }, []);

  // Scroll to bottom on message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const toggleSelectProperty = (prop: PropertyData) => {
    if (selectedProperties.some((p) => p.id === prop.id)) {
      setSelectedProperties(selectedProperties.filter((p) => p.id !== prop.id));
    } else {
      if (selectedProperties.length >= 4) {
        alert('You can compare up to 4 properties at a time.');
        return;
      }
      setSelectedProperties([...selectedProperties, prop]);
    }
  };

  const removeSelectedProperty = (id: string) => {
    setSelectedProperties(selectedProperties.filter((p) => p.id !== id));
  };

  async function sendMessage(text: string) {
    if (!text.trim() || busy) return;

    const userMessage: Msg = { role: 'user', content: text };
    const nextHistory = [...messages, userMessage];
    setMessages(nextHistory);
    setInput('');
    setBusy(true);

    try {
      const payload: any = {
        message: text,
        history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })),
        platform: platformFilter === 'all' ? null : platformFilter,
        city: cityFilter === 'all' ? null : cityFilter,
        purpose: purposeFilter === 'all' ? null : purposeFilter
      };

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      const assistantMessage: Msg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        properties: data.properties || [],
        destinations: data.destinations || []
      };

      setMessages([...nextHistory, assistantMessage]);
    } catch (err: any) {
      setMessages([
        ...nextHistory,
        {
          role: 'assistant',
          content: `⚠️ Note: The assistant encountered an issue contacting the model endpoint (${err.message}). Please ensure the backend service is running.`
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void sendMessage(input);
  }

  return (
    <main className="shell flex flex-col justify-between">
      {/* Top Header */}
      <div>
        <header className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-5 mb-6 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs tracking-widest uppercase font-bold text-amber-400 bg-amber-950/60 border border-amber-800/80 px-2.5 py-0.5 rounded-full">
                DarGlobal × Wasalt
              </span>
              <span className="text-xs tracking-widest uppercase text-sky-400 font-medium">
                Production AI Concierge
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold mt-2 tracking-tight">
              Property Intelligence <span className="text-sky-400">AI</span>
            </h1>
            <p className="text-slate-400 text-xs md:text-sm mt-1">
              Grounded conversational retrieval over verified luxury developments and Saudi real estate marketplace listings.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {stats && (
              <div className="hidden lg:flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Verified Properties</span>
                  <span className="font-semibold text-emerald-400">{stats.total_properties} Listings</span>
                </div>
                <div className="w-px h-6 bg-slate-800" />
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Cities Covered</span>
                  <span className="font-semibold text-sky-400">{stats.cities_covered} Metros</span>
                </div>
              </div>
            )}

            {selectedProperties.length > 0 && (
              <button
                onClick={() => setShowCompareModal(true)}
                className="px-3.5 py-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-sky-950 flex items-center gap-1.5 transition-all"
              >
                <span>⚖️</span> Compare ({selectedProperties.length})
              </button>
            )}

            <div className="text-xs rounded-full border border-emerald-800 bg-emerald-950/60 px-3 py-1.5 text-emerald-300 flex items-center gap-1.5 shrink-0">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              RAG & Qdrant Online
            </div>
          </div>
        </header>

        {/* Filter Bar */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-3.5 mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500 font-semibold uppercase text-[10px] mr-1">Platform:</span>
            {['all', 'darglobal', 'wasalt'].map((p) => (
              <button
                key={p}
                onClick={() => setPlatformFilter(p)}
                className={`chip ${platformFilter === p ? 'active' : ''}`}
              >
                {p === 'all' ? 'All Platforms' : p === 'darglobal' ? 'DarGlobal Luxury' : 'Wasalt Marketplace'}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500 font-semibold uppercase text-[10px] mr-1">City Filter:</span>
            {['all', 'riyadh', 'jeddah', 'dubai', 'muscat', 'london'].map((c) => (
              <button
                key={c}
                onClick={() => setCityFilter(c)}
                className={`chip ${cityFilter === c ? 'active' : ''}`}
              >
                {c === 'all' ? 'All Metros' : c.charAt(0).toUpperCase() + c.slice(1)}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-semibold uppercase text-[10px] mr-1">Purpose:</span>
            {['all', 'sale', 'rent'].map((purp) => (
              <button
                key={purp}
                onClick={() => setPurposeFilter(purp)}
                className={`chip ${purposeFilter === purp ? 'active' : ''}`}
              >
                {purp === 'all' ? 'All' : purp === 'sale' ? 'For Sale' : 'For Rent'}
              </button>
            ))}
          </div>
        </div>

        {/* Main Conversation Container */}
        <section className="panel p-4 md:p-6 mb-6">
          <div className="space-y-6 min-h-[420px] max-h-[62vh] overflow-y-auto pr-2">
            {messages.map((m, idx) => (
              <div key={idx} className="space-y-3">
                <div className={`bubble ${m.role === 'user' ? 'user' : 'assistant'}`}>
                  <div className="text-[10px] uppercase tracking-wider opacity-60 mb-1.5 flex items-center gap-1.5 font-bold">
                    {m.role === 'user' ? (
                      <>
                        <span>👤</span> You
                      </>
                    ) : (
                      <>
                        <span>🏛️</span> Property Intelligence Concierge
                      </>
                    )}
                  </div>
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</div>
                </div>

                {/* Property Cards */}
                {m.properties && m.properties.length > 0 && (
                  <div className="ml-2 pl-3 border-l-2 border-sky-500/40 my-3">
                    <div className="text-xs font-semibold text-slate-400 mb-2 flex items-center justify-between">
                      <span>MATCHED PROPERTIES ({m.properties.length})</span>
                      <span className="text-[11px] text-sky-400">Select properties to compare side-by-side</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {m.properties.map((prop) => (
                        <PropertyCard
                          key={prop.id}
                          property={prop}
                          isSelected={selectedProperties.some((p) => p.id === prop.id)}
                          onToggleSelect={toggleSelectProperty}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Sources & Official Destinations */}
                {((m.sources && m.sources.length > 0) || (m.destinations && m.destinations.length > 0)) && (
                  <div className="ml-2 space-y-2 pt-1">
                    {m.sources && m.sources.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mr-1">
                          Verified Sources:
                        </span>
                        {m.sources.map((src, i) => (
                          <SourceBadge key={i} source={src} />
                        ))}
                      </div>
                    )}

                    {m.destinations && m.destinations.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mr-1">
                          Official Portals:
                        </span>
                        {m.destinations.map((dest, i) => (
                          <a
                            key={i}
                            href={dest.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs px-2.5 py-0.5 rounded-full bg-sky-950/50 hover:bg-sky-900/60 border border-sky-800 text-sky-300 inline-flex items-center gap-1 transition"
                          >
                            <span>{dest.label}</span>
                            <span>↗</span>
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {busy && (
              <div className="bubble assistant text-sm text-slate-400 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
                Querying Qdrant vectors & reasoning with OpenRouter free model…
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Starter Chips */}
          <div className="mt-5 pt-4 border-t border-slate-800">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Suggested Intelligence Queries:
            </div>
            <div className="flex flex-wrap gap-2">
              {STARTER_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => void sendMessage(prompt)}
                  disabled={busy}
                  className="chip text-xs hover:border-sky-400 text-left"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="flex gap-2.5 mt-5">
            <input
              className="field flex-1 text-sm"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about DarGlobal luxury projects, Wasalt listings, prices, or compare locations…"
              disabled={busy}
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="btn-primary flex items-center gap-2 text-sm shrink-0"
            >
              <span>Send</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>
        </section>
      </div>

      {/* Comparison Modal */}
      {showCompareModal && (
        <CompareModal
          properties={selectedProperties}
          onClose={() => setShowCompareModal(false)}
          onRemove={removeSelectedProperty}
        />
      )}

      {/* Footer */}
      <footer className="text-xs text-slate-500 border-t border-slate-800 pt-4 pb-2 flex flex-col md:flex-row items-center justify-between gap-2">
        <div>
          <span>Property Intelligence AI · Powered by FastAPI, Qdrant, Next.js & OpenRouter</span>
        </div>
        <div className="text-right">
          <span>Grounded strictly on public data from DarGlobal & Wasalt. Confirm terms with official providers.</span>
        </div>
      </footer>
    </main>
  );
}
