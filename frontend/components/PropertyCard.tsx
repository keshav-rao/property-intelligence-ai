'use client';

import React from 'react';

export interface PropertyData {
  id: string;
  name?: string;
  title: string;
  platform: 'darglobal' | 'wasalt' | string;
  url: string;
  city: string;
  country: string;
  district?: string;
  property_type: string;
  purpose: string;
  price_display: string;
  price_numeric?: number;
  currency?: string;
  bedrooms?: string | number | null;
  area_sqm?: string | number | null;
  developer?: string;
  brand_partner?: string | null;
  amenities?: string[];
  description?: string;
  scraped_at?: string;
}

interface PropertyCardProps {
  property: PropertyData;
  isSelected?: boolean;
  onToggleSelect?: (prop: PropertyData) => void;
}

export default function PropertyCard({ property, isSelected, onToggleSelect }: PropertyCardProps) {
  const isDarGlobal = property.platform === 'darglobal';

  return (
    <div className={`property-card p-4 relative flex flex-col justify-between ${isSelected ? 'ring-2 ring-sky-400 border-sky-400' : ''}`}>
      <div>
        {/* Header badges */}
        <div className="flex items-center justify-between mb-2 gap-2">
          <span className={`text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full ${isDarGlobal ? 'badge-darglobal' : 'badge-wasalt'}`}>
            {isDarGlobal ? 'DarGlobal Luxury' : 'Wasalt Market'}
          </span>
          <span className="text-xs font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2 py-0.5 rounded-md">
            {property.price_display}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-sm line-clamp-2 text-white mb-1.5" title={property.title}>
          {property.name || property.title}
        </h3>

        {/* Location */}
        <div className="text-xs text-slate-400 flex items-center gap-1 mb-2.5">
          <svg className="w-3.5 h-3.5 text-sky-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="truncate">{property.district ? `${property.district}, ` : ''}{property.city}, {property.country}</span>
        </div>

        {/* Brand partner badge */}
        {property.brand_partner && (
          <div className="mb-2.5 text-[11px] bg-amber-950/40 border border-amber-800/60 text-amber-300 px-2 py-1 rounded inline-flex items-center gap-1.5">
            <span>✨</span>
            <span className="font-medium">Partner: {property.brand_partner}</span>
          </div>
        )}

        {/* Specs grid */}
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 py-2 border-y border-slate-800/80 mb-2.5">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Type</span>
            <span className="font-medium truncate block">{property.property_type}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Bedrooms</span>
            <span className="font-medium truncate block">{property.bedrooms ? `${property.bedrooms}` : 'Not Specified'}</span>
          </div>
          {property.area_sqm && (
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Area</span>
              <span className="font-medium truncate block">{property.area_sqm} SQM</span>
            </div>
          )}
          <div>
            <span className="text-slate-500 block text-[10px] uppercase">Purpose</span>
            <span className="font-medium truncate block capitalize">For {property.purpose}</span>
          </div>
        </div>

        {/* Amenities preview */}
        {property.amenities && property.amenities.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {property.amenities.slice(0, 3).map((a, i) => (
              <span key={i} className="text-[10px] bg-slate-800/90 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700/60">
                {a}
              </span>
            ))}
            {property.amenities.length > 3 && (
              <span className="text-[10px] text-slate-400">+{property.amenities.length - 3} more</span>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-800/50 mt-1">
        <a
          href={property.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-sky-400 hover:text-sky-300 inline-flex items-center gap-1 transition-colors font-medium"
        >
          View Source
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>

        {onToggleSelect && (
          <button
            onClick={() => onToggleSelect(property)}
            className={`text-xs px-2.5 py-1 rounded-md border transition-all ${
              isSelected
                ? 'bg-sky-500 border-sky-400 text-white font-semibold'
                : 'border-slate-700 bg-slate-800/60 text-slate-300 hover:border-slate-500'
            }`}
          >
            {isSelected ? '✓ Selected' : '+ Compare'}
          </button>
        )}
      </div>
    </div>
  );
}
