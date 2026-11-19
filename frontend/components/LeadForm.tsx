'use client';

import { FormEvent, useState } from 'react';
import { submitLead, type LeadFormUI } from '../lib/api';
import { ExternalIcon } from './Icons';

// Contact details go straight to /api/leads (never through the chat or the LLM),
// and only after the user ticks the consent box.

export default function LeadForm({ ui, sessionId }: { ui: LeadFormUI; sessionId: string | null }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [pref, setPref] = useState<'email' | 'phone' | 'whatsapp'>('email');
  const [note, setNote] = useState('');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<{ reference: string; official_url: string; message: string } | null>(null);

  const brand = ui.platform === 'darglobal' ? 'DarGlobal' : 'Wasalt';

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr('');
    if (!email.trim() && !phone.trim()) {
      setErr('Please add an email address or a phone number.');
      return;
    }
    setBusy(true);
    try {
      const r = await submitLead({
        name: name.trim(), email: email.trim() || undefined, phone: phone.trim() || undefined, platform: ui.platform,
        interest: ui.interest || undefined, project_id: ui.project_id, preferred_contact: pref,
        message: note.trim() || undefined, consent, session_id: sessionId,
      });
      setDone(r);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="lead" role="status">
        <h4>Thank you, {name.split(' ')[0]}</h4>
        <p className="done">Your enquiry is saved. Reference <span className="ref">{done.reference}</span></p>
        <p className="hint" style={{ marginBottom: 8 }}>
          This demo stores enquiries locally and does not send them to {brand}. To reach {brand}&apos;s team directly:
        </p>
        <a className={`action ${ui.platform}`} href={done.official_url} target="_blank" rel="noopener noreferrer">
          Continue on {brand} <ExternalIcon />
        </a>
      </div>
    );
  }

  return (
    <form className="lead" onSubmit={onSubmit} aria-label="Enquiry form">
      <h4>Talk to an advisor</h4>
      <div className="hint">{ui.interest ? <>About: <b>{ui.interest}</b></> : `Tell us how to reach you.`}</div>
      <label htmlFor="lf-name">Full name</label>
      <input id="lf-name" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} autoComplete="name" />
      <div className="two">
        <div>
          <label htmlFor="lf-email">Email</label>
          <input id="lf-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        </div>
        <div>
          <label htmlFor="lf-phone">Phone</label>
          <input id="lf-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+966" autoComplete="tel" />
        </div>
      </div>
      <label htmlFor="lf-pref">Preferred contact</label>
      <select id="lf-pref" value={pref} onChange={(e) => setPref(e.target.value as typeof pref)}>
        <option value="email">Email</option>
        <option value="phone">Phone call</option>
        <option value="whatsapp">WhatsApp</option>
      </select>
      <label htmlFor="lf-note">Anything else? (optional)</label>
      <textarea id="lf-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={600} />
      <div className="consent">
        <input id="lf-consent" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <label htmlFor="lf-consent" style={{ margin: 0 }}>I agree to be contacted about this enquiry. My details are not shared with the AI model.</label>
      </div>
      <button className="submit" type="submit" disabled={busy || !consent || name.trim().length < 2}>
        {busy ? 'Sending…' : 'Send enquiry'}
      </button>
      {err && <div className="err" role="alert">{err}</div>}
    </form>
  );
}
