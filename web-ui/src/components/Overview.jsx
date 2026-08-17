import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

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
    // Process incoming WebSocket messages
    if (messages.length > 0) {
      const latestMsg = messages[messages.length - 1];
      
      // Update data based on message type
      if (latestMsg.type === 'market_update' && data) {
        // Assume latestMsg contains new overview data
        setData((prev) => ({
          ...prev,
          // Update relevant fields
          regime: latestMsg.data.regime || prev.regime,
        }));
      }
    }
  }, [messages]);

  if (!data || !commandData) return <div className="p-4 text-slate-400">Loading Terminal...</div>;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      {/* COMMAND CENTER */}
      <div className="border border-brand-border bg-brand-card p-4 rounded-xl flex items-center justify-between">
        <div>
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Command Center</div>
          <div className="text-xl font-bold text-white">{commandData.market_state}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Recommended Action</div>
          <div className="text-lg font-bold text-brand-positive">{commandData.recommended_action}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Cash Target</div>
          <div className="text-lg font-bold text-brand-accent">{commandData.cash_target}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Best Factor</div>
          <div className="text-lg font-bold text-white">{commandData.best_factor}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Best Sector</div>
          <div className="text-lg font-bold text-white">{commandData.best_sector}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Top Idea</div>
          <button onClick={() => onSelectStock(commandData.top_idea)} className="text-lg font-bold text-brand-accent hover:underline">
            {commandData.top_idea}
          </button>
        </div>
      </div>

      {/* TOP ROW STATS */}
      <div className="grid grid-cols-4 gap-4">
        <div className="border border-brand-border bg-brand-card p-4 rounded-xl">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Regime</div>
          <div className="text-xl font-bold text-white">{data.regime.state}</div>
          <div className="text-xs text-brand-accent mt-1">{data.regime.confidence}% Confidence</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 rounded-xl">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Breadth</div>
          <div className="text-xl font-bold text-white">{data.market_health.pct_above_50dma}% &gt; 50DMA</div>
          <div className="text-xs text-slate-400 mt-1">Improving</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 rounded-xl">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Top Sector</div>
          <div className="text-xl font-bold text-white">{data.top_sector}</div>
        </div>
        <div className="border border-brand-border bg-brand-card p-4 rounded-xl">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Cash Level</div>
          <div className="text-xl font-bold text-brand-positive">{data.cash_allocation}%</div>
        </div>
      </div>

      {/* MARKET HEALTH */}
      <div className="border border-brand-border bg-brand-card p-4 rounded-xl">
        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">Market Health Score</div>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-white">{data.market_health.score}</div>
          <div className="flex-1 h-2 bg-brand-base rounded-full overflow-hidden">
             <div className="h-full bg-brand-positive" style={{ width: `${data.market_health.score}%` }}></div>
          </div>
        </div>
        <div className="flex justify-between mt-4 text-xs font-mono text-slate-400">
          <span>New Highs: <span className="text-brand-positive">{data.market_health.new_highs}</span></span>
          <span>New Lows: <span className="text-brand-negative">{data.market_health.new_lows}</span></span>
        </div>
      </div>

      {/* SPLIT ROW: OPPORTUNITIES & WATCHLIST */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-brand-border bg-brand-card p-4 rounded-xl h-64 overflow-y-auto custom-scrollbar">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">Top Opportunities</div>
          {/* Mock Opportunities list */}
          {[
            {sym: 'TRENT', score: 94},
            {sym: 'KALYANKJIL', score: 91},
            {sym: 'APARINDS', score: 88}
          ].map(o => (
            <div key={o.sym} onClick={() => onSelectStock(o.sym)} className="flex justify-between items-center py-2 border-b border-white/5 cursor-pointer hover:bg-white/5 px-2 rounded">
              <span className="font-bold text-white">{o.sym}</span>
              <span className="font-mono text-brand-accent">{o.score}</span>
            </div>
          ))}
        </div>
        
        <div className="border border-brand-border bg-brand-card p-4 rounded-xl h-64 overflow-y-auto custom-scrollbar">
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-4">Watchlist Events</div>
          {watchlist.map((w, i) => (
            <div key={i} onClick={() => onSelectStock(w.symbol)} className="flex items-center gap-3 py-2 border-b border-white/5 cursor-pointer hover:bg-white/5 px-2 rounded">
              <span className="font-bold text-white w-20">{w.symbol}</span>
              <span className="font-mono text-xs text-brand-positive">{w.event}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
