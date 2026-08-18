import React, { useEffect, useState } from 'react';

export default function MarketIntelligence() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/market_intelligence').then(r => r.json()).then(setData);
  }, []);

  if (!data) return <div className="p-4 text-slate-400">Loading Market Intelligence...</div>;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      <div className="text-xl font-bold text-slate-300 mb-4">Market Intelligence</div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-brand-border bg-brand-card p-4">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Market Breadth</div>
          <div className="text-2xl font-bold text-slate-300">{data.market_breadth}</div>
        </div>
        
        <div className="border border-brand-border bg-brand-card p-4">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Sector Rotation</div>
          <div className="text-2xl font-bold text-slate-300">{data.sector_rotation}</div>
        </div>

        <div className="border border-brand-border bg-brand-card p-4">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">New Highs / Lows</div>
          <div className="flex items-center gap-4">
            <div className="text-2xl font-bold text-brand-positive">{data.new_highs}</div>
            <div className="text-slate-500">vs</div>
            <div className="text-2xl font-bold text-brand-negative">{data.new_lows}</div>
          </div>
        </div>

        <div className="border border-brand-border bg-brand-card p-4">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Regime Changes</div>
          <div className="text-lg font-bold text-slate-300">{data.regime_changes}</div>
        </div>
      </div>
    </div>
  );
}
