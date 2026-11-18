'use client';

import React from 'react';
import { PropertyData } from './PropertyCard';

interface CompareModalProps {
  properties: PropertyData[];
  onClose: () => void;
  onRemove: (id: string) => void;
}

export default function CompareModal({ properties, onClose, onRemove }: CompareModalProps) {
  if (properties.length === 0) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span>⚖️</span> Side-by-Side Property Comparison
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Comparing {properties.length} properties across developer, location, pricing, and specs
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        {/* Comparison Table / Grid */}
        <div className="p-6 overflow-x-auto flex-1">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${properties.length}, minmax(260px, 1fr))` }}>
            {properties.map((p) => {
              const isDg = p.platform === 'darglobal';
              return (
                <div key={p.id} className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    {/* Header */}
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${isDg ? 'badge-darglobal' : 'badge-wasalt'}`}>
                        {isDg ? 'DarGlobal Luxury' : 'Wasalt Market'}
                      </span>
                      <button
                        onClick={() => onRemove(p.id)}
                        className="text-xs text-rose-400 hover:text-rose-300"
                        title="Remove from comparison"
                      >
                        Remove ✕
                      </button>
                    </div>

                    <h3 className="font-semibold text-sm text-white mb-2 line-clamp-2">
                      {p.name || p.title}
                    </h3>

                    {/* Matrix Rows */}
                    <div className="space-y-3 text-xs border-t border-slate-700/60 pt-3">
                      <div>
                        <span className="text-slate-500 uppercase text-[10px] block font-semibold">Price</span>
                        <span className="font-bold text-emerald-400 text-sm">{p.price_display}</span>
                      </div>

                      <div>
                        <span className="text-slate-500 uppercase text-[10px] block font-semibold">Location</span>
                        <span className="text-slate-200">{p.district ? `${p.district}, ` : ''}{p.city}, {p.country}</span>
                      </div>

                      <div>
                        <span className="text-slate-500 uppercase text-[10px] block font-semibold">Property Type & Purpose</span>
                        <span className="text-slate-200">{p.property_type} (For {p.purpose})</span>
                      </div>

                      <div>
                        <span className="text-slate-500 uppercase text-[10px] block font-semibold">Developer / Brand</span>
                        <span className="text-slate-200">
                          {p.developer || 'N/A'}
                          {p.brand_partner ? ` (Partner: ${p.brand_partner})` : ''}
                        </span>
                      </div>

                      <div>
                        <span className="text-slate-500 uppercase text-[10px] block font-semibold">Bedrooms & Built-up Area</span>
                        <span className="text-slate-200">
                          {p.bedrooms ? `${p.bedrooms} Beds` : 'Not specified'} · {p.area_sqm ? `${p.area_sqm} SQM` : 'N/A'}
                        </span>
                      </div>

                      <div>
                        <span className="text-slate-500 uppercase text-[10px] block font-semibold">Key Amenities</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {p.amenities && p.amenities.length > 0 ? (
                            p.amenities.slice(0, 5).map((a, i) => (
                              <span key={i} className="text-[10px] bg-slate-900 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">
                                {a}
                              </span>
                            ))
                          ) : (
                            <span className="text-slate-500">Standard amenities</span>
                          )}
                        </div>
                      </div>

                      {p.description && (
                        <div>
                          <span className="text-slate-500 uppercase text-[10px] block font-semibold">Summary</span>
                          <p className="text-slate-300 text-[11px] line-clamp-3 mt-0.5">{p.description}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <a
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 block text-center text-xs py-2 bg-sky-600/30 hover:bg-sky-600/50 text-sky-300 border border-sky-500/40 rounded-lg font-medium transition"
                  >
                    View Official Listing ↗
                  </a>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex justify-between items-center bg-slate-950/60 rounded-b-2xl">
          <span className="text-xs text-slate-400">
            Data sourced directly from verified DarGlobal and Wasalt public records.
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold"
          >
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
}
