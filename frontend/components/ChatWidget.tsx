'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { streamChat, type ChatMeta, type PropertyCardData } from '../lib/api';
import CompareTable from './CompareTable';
import { ChatIcon, CloseIcon, ConciergeMark, ExternalIcon, RestartIcon, SendIcon } from './Icons';
import LeadForm from './LeadForm';
import Markdown from './Markdown';
import PropertyCard from './PropertyCard';

type Msg =
  | { id: string; role: 'user'; text: string }
  | { id: string; role: 'bot'; text: string; streaming?: boolean; meta?: ChatMeta; error?: boolean; retry?: string };

const WELCOME: Msg[] = [
  { id: 'w1', role: 'bot', text: 'Welcome!' },
  {
    id: 'w2',
    role: 'bot',
    text:
      "Hello, I'm **Noor**, your property concierge for **DarGlobal** and **Wasalt**. I can find homes to buy or rent across Saudi Arabia, " +
      "explore DarGlobal's branded residences worldwide, compare options and connect you with an advisor. How can I help?",
    meta: {
      session_id: '', message_id: 'w2', intent: {}, filters: {}, recommendations: [], total_matches: 0, sources: [], actions: [], ui: null,
      suggested_replies: ['Help me buy a 3-bedroom apartment in Riyadh', 'Show me DarGlobal branded residences', 'I want to rent a villa in Jeddah'],
    },
  },
];

const FILTER_LABEL: Record<string, (v: string | number | boolean) => string | null> = {
  platform: (v) => (v === 'darglobal' ? 'DarGlobal' : 'Wasalt'),
  purpose: (v) => (v === 'rent' ? 'Rent' : 'Buy'),
  city: (v) => String(v).replace(/\b\w/g, (c) => c.toUpperCase()).replace('Khobar', 'Al Khobar'),
  country: (v) => String(v),
  property_type: (v) => String(v).replace(/^\w/, (c) => c.toUpperCase()),
  bedrooms: (v) => (v === 0 ? 'Studio' : `${v} bed`),
  budget_max: (v) => `≤ SAR ${Number(v) >= 1e6 ? `${(Number(v) / 1e6).toFixed(2).replace(/\.?0+$/, '')}M` : `${Math.round(Number(v) / 1000)}k`}`,
  brand: (v) => String(v),
  luxury: () => null,
};

let counter = 0;
const uid = () => `m${Date.now().toString(36)}${(counter++).toString(36)}`;

export default function ChatWidget({ prompt }: { prompt: { text: string; n: number } | null }) {
  const [open, setOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  // On phones the chat is the product: open it full-screen on first load.
  useEffect(() => {
    if (window.matchMedia('(max-width: 560px)').matches) setMobileOpen(true);
  }, []);
  const [messages, setMessages] = useState<Msg[]>(WELCOME);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selected, setSelected] = useState<PropertyCardData[]>([]);
  const bodyRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const send = useCallback(
    async (text: string, compareIds?: string[]) => {
      const clean = text.trim();
      if (!clean || busy) return;
      setBusy(true);
      setInput('');
      const botId = uid();
      setMessages((m) => [...m, { id: uid(), role: 'user', text: clean }, { id: botId, role: 'bot', text: '', streaming: true }]);
      const patch = (fn: (b: Extract<Msg, { role: 'bot' }>) => Partial<Extract<Msg, { role: 'bot' }>>) =>
        setMessages((m) => m.map((x) => (x.id === botId && x.role === 'bot' ? { ...x, ...fn(x) } : x)));
      abortRef.current = new AbortController();
      try {
        await streamChat(
          { message: clean, session_id: sessionId, compare_ids: compareIds },
          {
            onMeta: (meta) => {
              setSessionId(meta.session_id);
              patch(() => ({ meta }));
            },
            onToken: (t) => patch((b) => ({ text: b.text + t })),
            onDone: (d) => patch(() => ({ text: d.answer, streaming: false })),
          },
          abortRef.current.signal,
        );
      } catch {
        patch(() => ({
          text: "I couldn't reach the server just now. Please check your connection and try again.",
          streaming: false, error: true, retry: clean,
        }));
      } finally {
        setBusy(false);
        inputRef.current?.focus();
      }
    },
    [busy, sessionId],
  );

  // prompts from the landing page ("Try asking" chips)
  useEffect(() => {
    if (prompt) {
      setOpen(true);
      setMobileOpen(true);
      send(prompt.text);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prompt?.n]);

  function toggleCompare(item: PropertyCardData) {
    setSelected((s) => (s.some((x) => x.id === item.id) ? s.filter((x) => x.id !== item.id) : s.length >= 3 ? s : [...s, item]));
  }

  function restart() {
    abortRef.current?.abort();
    setSelected([]);
    setMessages(WELCOME);
    if (sessionId) fetch(`/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: 'start over', session_id: sessionId }) }).catch(() => {});
  }

  const lastBotIdx = messages.map((m) => m.role).lastIndexOf('bot');

  if (!open) {
    return (
      <button className="launcher" onClick={() => { setOpen(true); setMobileOpen(true); }} aria-label="Open property concierge chat">
        <ChatIcon />
      </button>
    );
  }

  return (
    <>
      <section className={`widget ${mobileOpen ? 'open-mobile' : ''}`} aria-label="Property concierge chat">
        <header className="w-head">
          <div>
            <h2>Property Concierge</h2>
            <div className="sub"><span className="dot-live" aria-hidden="true" /> DarGlobal × Wasalt · AI assistant</div>
          </div>
          <div className="spacer" />
          <button className="icon-btn" onClick={restart} aria-label="Start a new conversation" title="Start over"><RestartIcon /></button>
          <button className="icon-btn" onClick={() => { setOpen(false); setMobileOpen(false); }} aria-label="Close chat" title="Close"><CloseIcon /></button>
        </header>

        <div className="w-body" ref={bodyRef} aria-live="polite" aria-relevant="additions text">
          <div className="agent">
            <div className="avatar"><ConciergeMark size={30} /></div>
            <div>
              <div className="name">Noor</div>
              <div className="role">AI concierge · answers from official DarGlobal and Wasalt pages</div>
            </div>
          </div>

          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={m.id} className="msg user"><div className="bubble">{m.text}</div></div>
            ) : (
              <BotMessage
                key={m.id}
                m={m}
                isLast={i === lastBotIdx}
                busy={busy}
                selected={selected}
                sessionId={sessionId}
                onSend={send}
                onToggleCompare={toggleCompare}
              />
            ),
          )}
        </div>

        {selected.length > 0 && (
          <div className="tray" role="region" aria-label="Comparison tray">
            <span>{selected.length} selected for comparison</span>
            <span className="spacer" />
            <button className="clear" onClick={() => setSelected([])}>Clear</button>
            <button
              className="go"
              disabled={selected.length < 2 || busy}
              onClick={() => { const ids = selected.map((s) => s.id); setSelected([]); send(`Compare ${selected.map((s) => s.title.split(',')[0]).join(' and ')}`, ids); }}
            >
              Compare {selected.length >= 2 ? selected.length : ''}
            </button>
          </div>
        )}

        <footer className="w-foot">
          <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
            <label htmlFor="composer-input" className="sr">Message</label>
            <textarea
              id="composer-input"
              ref={inputRef}
              rows={1}
              value={input}
              placeholder="Type something to send..."
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              maxLength={1200}
            />
            <button className="send" type="submit" disabled={!input.trim() || busy} aria-label="Send message"><SendIcon /></button>
          </form>
          <div className="disclaimer">AI answers from public DarGlobal &amp; Wasalt pages. Confirm prices and availability on the official sites.</div>
        </footer>
      </section>
      {!mobileOpen && (
        <button className="launcher mobile-only" onClick={() => setMobileOpen(true)} aria-label="Open property concierge chat">
          <ChatIcon />
        </button>
      )}
    </>
  );
}

function BotMessage({
  m, isLast, busy, selected, sessionId, onSend, onToggleCompare,
}: {
  m: Extract<Msg, { role: 'bot' }>;
  isLast: boolean;
  busy: boolean;
  selected: PropertyCardData[];
  sessionId: string | null;
  onSend: (t: string, ids?: string[]) => void;
  onToggleCompare: (p: PropertyCardData) => void;
}) {
  const meta = m.meta;
  const filters = meta
    ? Object.entries(meta.filters)
        .map(([k, v]) => (FILTER_LABEL[k] ? FILTER_LABEL[k](v) : null))
        .filter(Boolean) as string[]
    : [];
  const showFilters = meta?.intent?.name === 'search' && filters.length > 0;
  const cards = meta?.recommendations || [];
  return (
    <div className="msg bot">
      <div className="bubble">
        {m.text ? <Markdown text={m.text} /> : <span className="typing" aria-label="Noor is typing"><i /><i /><i /></span>}
        {m.streaming && m.text && <span className="caret" aria-hidden="true" />}
      </div>

      {showFilters && !m.streaming && (
        <div className="meta-row" aria-label="Your search">
          {filters.map((f) => <span key={f} className="filter-chip">{f}</span>)}
        </div>
      )}

      {cards.length > 0 && (
        <>
          <div className="cards-head">
            <span>
              {meta!.total_matches > cards.length ? <>Top <b>{cards.length}</b> of {meta!.total_matches}</> : <><b>{cards.length}</b> {cards.length === 1 ? 'result' : 'results'}</>}
            </span>
            {cards.length > 1 && <span>Scroll →</span>}
          </div>
          <div className="cards">
            {cards.map((c) => (
              <PropertyCard key={c.id} item={c} selected={selected.some((s) => s.id === c.id)} onToggleCompare={onToggleCompare} onAsk={(t) => onSend(t)} />
            ))}
          </div>
        </>
      )}

      {meta?.also && meta.also.items.length > 0 && !m.streaming && (
        <div className="also">
          <div className="cards-head"><span><b>Also:</b> {meta.also.title}</span></div>
          <div className="cards">
            {meta.also.items.map((c) => (
              <PropertyCard key={c.id} item={c} selected={selected.some((s) => s.id === c.id)} onToggleCompare={onToggleCompare} onAsk={(t) => onSend(t)} />
            ))}
          </div>
        </div>
      )}

      {meta?.ui?.type === 'compare' && <CompareTable ui={meta.ui} />}
      {meta?.ui?.type === 'lead_form' && <LeadForm ui={meta.ui} sessionId={sessionId} />}

      {meta && meta.actions.length > 0 && !m.streaming && (
        <div className="actions">
          {meta.actions.map((a) => (
            <a key={a.url} className={`action ${a.platform}`} href={a.url} target="_blank" rel="noopener noreferrer">
              {a.label} <ExternalIcon />
            </a>
          ))}
        </div>
      )}

      {meta && meta.sources.length > 0 && !m.streaming && (
        <div className="sources">
          <span>Sources:</span>
          {meta.sources.slice(0, 4).map((s) => (
            <a key={s.url + s.title} href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>
          ))}
        </div>
      )}

      {m.error && m.retry && (
        <div className="qr"><button onClick={() => onSend(m.retry!)} disabled={busy}>Try again</button></div>
      )}

      {isLast && !m.streaming && meta && meta.suggested_replies.length > 0 && (
        <div className={`qr ${meta.suggested_replies.length > 3 ? 'wrap' : ''}`} role="group" aria-label="Suggested replies">
          {meta.suggested_replies.map((r) => (
            <button key={r} onClick={() => onSend(r)} disabled={busy}>{r}</button>
          ))}
        </div>
      )}
    </div>
  );
}
