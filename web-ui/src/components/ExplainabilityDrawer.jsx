import React, { useEffect, useState } from 'react';

export default function ExplainabilityDrawer({ stock, onClose }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (stock) {
      setData(null);
      fetch(`/api/explain/${stock}`).then(r => r.json()).then(setData);
    }
  }, [stock]);

  if (!stock) return null;

  return (
    <div className="w-96 border-l border-brand-border bg-brand-base flex flex-col h-full absolute right-0 top-0 z-50 shadow-2xl transition-transform duration-300">
      {/* Header */}
      <div className="p-4 border-b border-brand-border flex justify-between items-start bg-brand-card">
        <div>
          <div className="text-3xl font-bold text-white">{stock}</div>
          {data ? (
             <div className="flex gap-2 mt-2">
                <span className="px-2 py-1 bg-brand-accent/10 text-brand-accent text-xs font-mono rounded">MB Score: {data.score}</span>
                <span className="px-2 py-1 bg-white/5 text-slate-300 text-xs font-mono rounded">Opp: {data.opportunity_score}</span>
             </div>
          ) : <div className="text-xs text-slate-500 mt-2">Loading context...</div>}
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-white p-2">✕</button>
      </div>

      {data && (
        <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
          
          {/* Layer 1: Why It Matters */}
          <div className="border border-brand-border bg-brand-card rounded-xl overflow-hidden">
            <div className="bg-white/5 px-3 py-2 border-b border-brand-border text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Why It Matters
            </div>
            <div className="p-3">
              <div className="text-lg font-bold text-white mb-3">Rank #{data.why_it_matters.rank}</div>
              <div className="space-y-1">
                {data.why_it_matters.positives.map((p, i) => (
                  <div key={i} className="flex gap-2 text-sm text-brand-positive">
                    <span>+</span><span>{p}</span>
                  </div>
                ))}
                {data.why_it_matters.negatives.map((n, i) => (
                  <div key={i} className="flex gap-2 text-sm text-brand-negative">
                    <span>-</span><span>{n}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Layer 2: Factor Contributions */}
          <div className="border border-brand-border bg-brand-card rounded-xl overflow-hidden">
            <div className="bg-white/5 px-3 py-2 border-b border-brand-border text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Factor Contributions
            </div>
            <div className="p-3 space-y-3">
              {Object.entries(data.factor_contributions).map(([factor, val]) => (
                <div key={factor}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400 capitalize">{factor}</span>
                    <span className="text-white font-mono">+{val}</span>
                  </div>
                  <div className="h-1.5 bg-brand-base rounded-full overflow-hidden">
                    <div className="h-full bg-brand-accent" style={{width: `${(val/30)*100}%`}}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Layer 3: Historical Evolution */}
          <div className="border border-brand-border bg-brand-card rounded-xl overflow-hidden">
            <div className="bg-white/5 px-3 py-2 border-b border-brand-border text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Score Evolution
            </div>
            <div className="p-3 flex justify-between items-center text-sm font-mono text-slate-300">
               {data.historical_evolution.map((s, i) => (
                 <React.Fragment key={i}>
                    <span className={i === data.historical_evolution.length - 1 ? 'text-brand-accent font-bold' : ''}>{s}</span>
                    {i < data.historical_evolution.length - 1 && <span className="text-slate-600">→</span>}
                 </React.Fragment>
               ))}
            </div>
          </div>

          {/* Layer 4: Expected Behavior */}
          <div className="border border-brand-border bg-brand-card rounded-xl overflow-hidden">
            <div className="bg-white/5 px-3 py-2 border-b border-brand-border text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Alpha Expectation
            </div>
            <div className="p-3 grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-slate-500 mb-1">30D Alpha</div>
                <div className="text-lg font-bold text-brand-positive">{data.expected_behavior['30d_alpha']}</div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 mb-1">90D Alpha</div>
                <div className="text-lg font-bold text-brand-positive">{data.expected_behavior['90d_alpha']}</div>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
