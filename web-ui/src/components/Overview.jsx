import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { AreaChart, Area, ResponsiveContainer, YAxis } from 'recharts';

export default function Overview({ onSelectStock }) {
  const [data, setData] = useState(null);
  const [commandData, setCommandData] = useState(null);
  const [watchlist, setWatchlist] = useState([]);

  const { messages } = useWebSocket('/ws/signals');

  useEffect(() => {
    fetch('/api/overview').then(r => r.json()).then(setData);
    fetch('/api/command_center').then(r => r.json()).then(setCommandData);
    fetch('/api/watchlist/events').then(r => r.json()).then(setWatchlist);
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      const latestMsg = messages[messages.length - 1];
      if (latestMsg.type === 'market_update' && data) {
        setData((prev) => ({
          ...prev,
          regime: latestMsg.data.regime || prev.regime,
        }));
      }
    }
  }, [messages]);

  if (!data || !commandData) return <div className="p-4 text-slate-400">Loading Terminal...</div>;

  const heartbeatData = Array.from({length: 40}, (_, i) => ({ val: Math.random() * 10 + 10 }));

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* NEURAL HEARTBEAT */}
      <div className="border border-brand-border bg-brand-card p-4 relative rounded-lg shadow-sm">
        <div className="absolute top-4 left-4 z-10">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Neural Heartbeat</div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black font-mono text-brand-positive">18</span>
            <span className="text-[10px] text-slate-500 font-bold">ms</span>
          </div>
          <div className="mt-2 text-[8px] text-slate-500 uppercase tracking-widest">Queue Depth: <span className="text-slate-300 font-mono">0</span></div>
        </div>
        <div className="h-32 w-full mt-8">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={heartbeatData}>
              <defs>
                <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--secondary)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--secondary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <YAxis domain={['dataMin - 5', 'dataMax + 5']} hide />
              <Area type="step" dataKey="val" stroke="var(--secondary)" fillOpacity={1} fill="url(#colorVal)" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* MARKET HEALTH SCORE */}
      <div className="border border-brand-border bg-brand-card p-6 flex flex-col items-center justify-center relative rounded-lg shadow-sm">
        <div className="absolute top-4 left-4 text-[10px] text-slate-500 uppercase font-bold tracking-widest">Market Health Score</div>
        <div className="text-7xl font-bold text-slate-300 font-mono my-4">{data.market_health.score}</div>
        <div className="w-full max-w-2xl h-3 bg-brand-base overflow-hidden border border-brand-border rounded-full">
           <div className="h-full bg-brand-positive rounded-full" style={{ width: `${data.market_health.score}%` }}></div>
        </div>
        <div className="flex w-full max-w-2xl justify-between mt-2 text-xs font-mono text-slate-600">
          <span>New Highs: <span className="text-brand-positive">{data.market_health.new_highs}</span></span>
          <span>New Lows: <span className="text-brand-negative">{data.market_health.new_lows}</span></span>
        </div>
      </div>

      {/* COMMAND CENTER (6 Cards) */}
      <div className="grid grid-cols-6 gap-4">
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Market State</div>
          <div className="text-lg font-bold text-slate-300 leading-tight">{commandData.market_state}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Recommended Action</div>
          <div className="text-lg font-bold text-brand-positive leading-tight">{commandData.recommended_action}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Cash Target</div>
          <div className="text-lg font-bold text-brand-accent leading-tight">{commandData.cash_target}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Best Factor</div>
          <div className="text-lg font-bold text-slate-300 leading-tight">{commandData.best_factor}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Best Sector</div>
          <div className="text-lg font-bold text-slate-300 leading-tight">{commandData.best_sector}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between cursor-pointer hover:bg-brand-base rounded-lg shadow-sm transition-colors" onClick={() => onSelectStock(commandData.top_idea)}>
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Top Idea</div>
          <div className="text-lg font-bold text-brand-accent leading-tight">{commandData.top_idea}</div>
        </div>
      </div>

      {/* TOP ROW STATS (4 Cards) */}
      <div className="grid grid-cols-4 gap-4">
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Regime</div>
          <div className="text-xl font-bold text-slate-300">{data.regime.state}</div>
          <div className="text-xs text-brand-accent mt-1">{data.regime.confidence}% Confidence</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Breadth</div>
          <div className="text-xl font-bold text-slate-300">{data.market_health.pct_above_50dma}% &gt; 50DMA</div>
          <div className="text-xs text-slate-400 mt-1">Improving</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Top Sector</div>
          <div className="text-xl font-bold text-slate-300">{data.top_sector}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 flex flex-col justify-between rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-2">Cash Level</div>
          <div className="text-xl font-bold text-brand-positive">{data.cash_allocation}%</div>
        </div>
      </div>

      {/* SPLIT ROW: OPPORTUNITIES & WATCHLIST */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-brand-border bg-brand-card p-4 h-64 overflow-y-auto custom-scrollbar rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">Top Opportunities</div>
          {[
            {sym: 'TRENT', score: 94},
            {sym: 'KALYANKJIL', score: 91},
            {sym: 'APARINDS', score: 88}
          ].map(o => (
            <div key={o.sym} onClick={() => onSelectStock(o.sym)} className="flex justify-between items-center py-2 border-b border-brand-border cursor-pointer hover:bg-brand-base px-2 transition-colors">
              <span className="font-bold text-slate-300">{o.sym}</span>
              <span className="font-mono text-brand-accent">{o.score}</span>
            </div>
          ))}
        </div>
        
        <div className="border border-brand-border bg-brand-card p-4 h-64 overflow-y-auto custom-scrollbar rounded-lg shadow-sm">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">Watchlist Events</div>
          {watchlist.map((w, i) => (
            <div key={i} onClick={() => onSelectStock(w.symbol)} className="flex items-center gap-3 py-2 border-b border-brand-border cursor-pointer hover:bg-brand-base px-2 transition-colors">
              <span className="font-bold text-slate-300 w-20">{w.symbol}</span>
              <span className="font-mono text-xs text-brand-positive">{w.event}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
