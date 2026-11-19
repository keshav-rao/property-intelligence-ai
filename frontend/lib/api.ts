// Typed client for the FastAPI backend. Requests go to /api/* on the same origin
// (Next.js rewrites them to the backend in development; Caddy routes them in production).

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export type Platform = 'darglobal' | 'wasalt';

export interface PropertyCardData {
  id: string;
  platform: Platform;
  kind: 'project' | 'listing';
  title: string;
  brand?: string | null;
  city: string;
  country: string;
  district?: string | null;
  property_type: string;
  type_label: string;
  purpose: 'sale' | 'rent';
  bedrooms_label?: string | null;
  area_label?: string | null;
  price_label: string;
  price?: number | null;
  completion?: string | null;
  status?: string | null;
  image?: string | null;
  url: string;
  source: string;
  collected_at?: string | null;
}

export interface LinkAction {
  label: string;
  url: string;
  platform: Platform;
  key?: string;
}

export interface Source {
  title: string;
  url: string;
  platform: Platform;
}

export interface CompareUI {
  type: 'compare';
  columns: PropertyCardData[];
  rows: { label: string; values: string[] }[];
}

export interface LeadFormUI {
  type: 'lead_form';
  platform: Platform;
  interest: string;
  project_id: string | null;
}

export interface ChatMeta {
  session_id: string;
  message_id: string;
  intent: { name?: string; platform?: Platform | null; step?: string };
  filters: Record<string, string | number | boolean>;
  recommendations: PropertyCardData[];
  total_matches: number;
  sources: Source[];
  actions: LinkAction[];
  suggested_replies: string[];
  ui: CompareUI | LeadFormUI | null;
  also?: { title: string; items: PropertyCardData[] };
}

export interface StreamHandlers {
  onMeta: (m: ChatMeta) => void;
  onToken: (t: string) => void;
  onDone: (d: { answer: string; llm: string | null; grounded: boolean }) => void;
}

/** POST /api/chat/stream and parse the Server-Sent Events it returns. */
export async function streamChat(
  body: { message: string; session_id?: string | null; compare_ids?: string[] },
  h: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Chat request failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = 'message';
      let data = '';
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
      }
      if (!data) continue;
      const payload = JSON.parse(data);
      if (event === 'meta') h.onMeta(payload);
      else if (event === 'token') h.onToken(payload.t);
      else if (event === 'done') h.onDone(payload);
    }
  }
}

export interface LeadPayload {
  name: string;
  email?: string;
  phone?: string;
  platform: Platform;
  interest?: string;
  project_id?: string | null;
  preferred_contact?: 'email' | 'phone' | 'whatsapp';
  message?: string;
  consent: boolean;
  session_id?: string | null;
}

export async function submitLead(p: LeadPayload): Promise<{ reference: string; official_url: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/leads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Something went wrong. Please try again.');
  return data;
}

export async function getStats(): Promise<{
  darglobal_projects: number;
  darglobal_countries: string[];
  wasalt_listings: number;
  wasalt_cities: string[];
} | null> {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}
