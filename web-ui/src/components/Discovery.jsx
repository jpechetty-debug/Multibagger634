import React, { useEffect, useState } from 'react';

export default function Discovery({ onSelectStock }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/discovery').then(r => r.json()).then(setData);
  }, []);

  if (!data) return <div className="p-4 text-slate-400">Loading Discovery Engine...</div>;

  const renderSection = (title, items, formatter) => (
    <div className="border border-brand-border bg-brand-card flex flex-col h-64">
      <div className="p-3 border-b border-brand-border bg-white/5">
        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">{title}</div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 custom-scrollbar">
        {items.map((item, i) => (
          <div key={i} onClick={() => onSelectStock(item.symbol || item)} className="flex justify-between items-center py-2 px-2 border-b border-white/5 hover:bg-white/5 cursor-pointer">
             {formatter(item)}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      <div className="text-xl font-bold text-slate-300 mb-4">Discovery Engine</div>
      <div className="grid grid-cols-3 gap-4">
        {renderSection("Future Compounders", data.future_compounders, item => (
          <>
            <span className="font-bold text-slate-300">{item.symbol}</span>
            <div className="text-right">
              <div className="text-xs text-brand-positive">ROCE {item.roce}%</div>
              <div className="text-[10px] text-slate-400">Sales CAGR {item.sales_cagr}%</div>
            </div>
          </>
        ))}
        {renderSection("Emerging Leaders", data.emerging_leaders, item => (
          <>
            <span className="font-bold text-slate-300">{item.symbol}</span>
            <span className="font-mono text-brand-accent">Score {item.score}</span>
          </>
        ))}
        {renderSection("RS Acceleration", data.rs_acceleration, item => (
          <>
            <span className="font-bold text-slate-300">{item.symbol}</span>
            <span className="font-mono text-brand-positive">{item.rs_change} RS</span>
          </>
        ))}
        {renderSection("Earnings Acceleration", data.earnings_acceleration, item => (
          <>
            <span className="font-bold text-slate-300">{item.symbol}</span>
            <span className="font-mono text-[9px] text-brand-accent">{item.pattern}</span>
          </>
        ))}
        {renderSection("Sector Breakouts", data.sector_breakouts, item => (
          <span className="font-bold text-slate-300">{item}</span>
        ))}
      </div>
    </div>
  );
}
