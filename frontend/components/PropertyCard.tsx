'use client';

import { useState } from 'react';
import type { PropertyCardData } from '../lib/api';
import { PinIcon } from './Icons';

interface Props {
  item: PropertyCardData;
  selected: boolean;
  onToggleCompare: (item: PropertyCardData) => void;
  onAsk: (text: string) => void;
}

export default function PropertyCard({ item, selected, onToggleCompare, onAsk }: Props) {
  const [imgOk, setImgOk] = useState(Boolean(item.image));
  const isDG = item.platform === 'darglobal';
  const place = [item.district, item.city, isDG ? item.country : null].filter(Boolean).join(', ');
  const sold = (item.status || '').toLowerCase().includes('sold');
  const facts = [item.bedrooms_label, item.area_label, isDG ? item.completion && `Handover ${item.completion}` : item.purpose === 'rent' ? 'For rent' : 'For sale']
    .filter(Boolean) as string[];

  return (
    <article className={`pcard ${item.platform}`} aria-label={item.title}>
      <div className="img">
        {imgOk && item.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.image} alt={item.title} loading="lazy" onError={() => setImgOk(false)} referrerPolicy="no-referrer" />
        ) : (
          <div className="ph">{item.type_label}</div>
        )}
        <span className={`badge ${item.platform}`}>{isDG ? 'DarGlobal' : 'Wasalt'}</span>
        {isDG && item.status && (sold || /premiere/i.test(item.status)) && (
          <span className={`badge status ${sold ? 'sold' : ''}`}>{sold ? 'Sold out' : '1 of 1'}</span>
        )}
      </div>
      <div className="body">
        <div className={`price ${item.price ? '' : 'req'}`}>{item.price_label}</div>
        <div className="title">{item.title}</div>
        <div className="where"><PinIcon /> {place}</div>
        {item.brand && <div className="brand">{item.brand}</div>}
        {facts.length > 0 && (
          <div className="facts">{facts.slice(0, 3).map((f) => <span key={f}>{f}</span>)}</div>
        )}
        {!isDG && <div className="stamp">Source: Wasalt.sa · snapshot 19 Nov 2026</div>}
        <div className={`row ${isDG ? 'three' : ''}`}>
          <a className="primary" href={item.url} target="_blank" rel="noopener noreferrer">
            {isDG ? 'View project' : 'View listing'}
          </a>
          <button type="button" className={selected ? 'on' : ''} aria-pressed={selected} onClick={() => onToggleCompare(item)}>
            {selected ? '✓ Compare' : 'Compare'}
          </button>
          {isDG && (
            <button type="button" onClick={() => onAsk(`Tell me about ${item.title.split(',')[0]}`)}>Details</button>
          )}
        </div>
      </div>
    </article>
  );
}
