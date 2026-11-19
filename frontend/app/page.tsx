'use client';

import { useEffect, useState } from 'react';
import ChatWidget from '../components/ChatWidget';
import { getStats } from '../lib/api';

const TRY = [
  '3-bedroom apartment in Riyadh under SAR 1.2M',
  'Rent a villa in Jeddah',
  'Lamborghini-inspired villas in Spain',
  'Compare DG1 and Les Vagues',
  'How do Wasalt auctions work?',
  'Tell me about Trump Tower Jeddah',
];

export default function Home() {
  const [prompt, setPrompt] = useState<{ text: string; n: number } | null>(null);
  const [stats, setStats] = useState<{ dg: number; ws: number; cities: number; countries: number } | null>(null);

  useEffect(() => {
    getStats().then((s) => s && setStats({ dg: s.darglobal_projects, ws: s.wasalt_listings, cities: s.wasalt_cities.length, countries: s.darglobal_countries.length }));
  }, []);

  return (
    <main className="page">
      <section className="hero">
        <div className="brandline">
          <span className="dg">DarGlobal</span><span className="x">×</span><span className="ws">Wasalt</span>
        </div>
        <h1>
          Find the right home, <em>in one conversation.</em>
        </h1>
        <p className="intro">
          Property Intelligence AI brings DarGlobal&apos;s branded residences and Wasalt&apos;s Saudi listings into a single concierge.
          Start with a loose idea; it asks only what it needs, recommends real options and sends you to the right official page.
        </p>

        <div className="caps">
          <div className="cap"><b>Guided or free-form</b><span>Tap a suggestion or just type, in your own words.</span></div>
          <div className="cap"><b>Real recommendations</b><span>Ranked from official project pages and Wasalt listings.</span></div>
          <div className="cap"><b>Compare side by side</b><span>Location, size, brand, price and handover in one table.</span></div>
          <div className="cap"><b>Private enquiries</b><span>Contact details go to the enquiry form, never to the AI.</span></div>
        </div>

        <div className="stats" aria-label="Data coverage">
          <div className="stat"><b>{stats?.dg ?? 38}</b><span>DarGlobal projects</span></div>
          <div className="stat"><b>{stats?.countries ?? 6}</b><span>Countries</span></div>
          <div className="stat"><b>{stats?.ws ?? 199}</b><span>Wasalt listings</span></div>
          <div className="stat"><b>{stats?.cities ?? 6}</b><span>Saudi cities</span></div>
        </div>

        <div className="try">Try asking</div>
        <div className="try-list">
          {TRY.map((t) => (
            <button key={t} className="try-chip" onClick={() => setPrompt({ text: t, n: Date.now() })}>{t}</button>
          ))}
        </div>

        <p className="fineprint">
          Independent assessment project, not affiliated with DarGlobal or Wasalt. DarGlobal data comes from darglobal.co.uk project pages;
          Wasalt listings are a dated snapshot of public wasalt.sa pages (Source: Wasalt.sa). Always confirm prices and availability on the official sites.
        </p>
      </section>

      <ChatWidget prompt={prompt} />
    </main>
  );
}
