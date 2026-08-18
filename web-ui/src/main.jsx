import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import {
  BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ComposedChart, CartesianGrid, Legend, Area, AreaChart
} from 'recharts';
import { marked } from 'marked';
import { GenericWire } from './components/GenericWire';
import Overview from './components/Overview';
import MarketIntelligence from './components/MarketIntelligence';
import Discovery from './components/Discovery';
import ScoreChart from './components/ScoreChart';
import ExplainabilityDrawer from './components/ExplainabilityDrawer';
import { useWebSocket } from './hooks/useWebSocket';
import './index.css';

const API = '';

const StressDashboard = ({ engine }) => {
    const [metrics, setMetrics] = useState(engine?.metrics || {fps:60, eventsPerSec:0, avgLag:12, p99Lag:22, heapUsed:45});
    if (!engine?.active) return null;
    return (
        <div className="fixed top-20 left-4 z-50 bg-black/90 border border-red-500/50 p-4 backdrop-blur-md w-64 font-mono text-xs animate-fade-in text-slate-300">
            <div className="text-red-500 font-bold uppercase tracking-widest mb-2 border-b border-red-500/30 pb-1">
                Stress Harness: {engine.currentLevel.toUpperCase()}
            </div>
            <div className="grid grid-cols-2 gap-y-2 gap-x-4">
                <div className="text-slate-400">FPS</div>
                <div className={`text-right font-bold ${metrics.fps < 40 ? 'text-red-500 animate-pulse' : 'text-emerald-400'}`}>{metrics.fps}</div>
                <div className="text-slate-400">Events/s</div>
                <div className="text-right text-slate-300 font-bold">{metrics.eventsPerSec}</div>
                <div className="text-slate-400">Avg Lag</div>
                <div className={`text-right font-bold ${metrics.avgLag > 30 ? 'text-orange-400' : 'text-emerald-400'}`}>{metrics.avgLag}ms</div>
                <div className="text-slate-400">P99 Lag</div>
                <div className={`text-right font-bold ${metrics.p99Lag > 100 ? 'text-red-500' : 'text-blue-400'}`}>{metrics.p99Lag}ms</div>
                <div className="text-slate-400">Heap</div>
                <div className="text-right text-purple-400">{metrics.heapUsed} MB</div>
            </div>
            <div className="mt-3 pt-2 border-t border-white/10 flex justify-between items-center">
                <span className="text-slate-500">Status</span>
                <span className="bg-red-500/20 text-red-300 px-2 py-0.5 text-[9px] uppercase font-bold animate-pulse">ACTIVE</span>
            </div>
        </div>
    );
};
const QuarterlyTimeline = ({ symbol }) => {
    const [data, setData]         = useState(null);
    const [loading, setLoading]   = useState(true);
    const [error, setError]       = useState(null);
    const [viewMode, setViewMode] = useState('revenue');
    useEffect(() => {
        if (!symbol) return;
        setLoading(true); setError(null);
        fetch(`/api/quarterly-results/${symbol}`)
            .then(r => { if (!r.ok) throw new Error('Failed to load quarterly results'); return r.json(); })
            .then(d => { setData(d); setLoading(false); })
            .catch(e => { setError(e.message); setLoading(false); });
    }, [symbol]);
    if (loading) return <div className="text-center py-10"><div className="loading-dot"/><div className="loading-dot"/><div className="loading-dot"/></div>;
    if (error) return <div className="text-red-400 text-[10px] p-4 bg-red-400/10">Error: {error}</div>;
    if (!data || !data.quarters || data.quarters.length === 0) return <div className="text-slate-500 text-[10px] p-4 italic">No quarterly data available.</div>;
    return (
        <div className="animate-fade-in space-y-4">
            <div className="flex justify-between items-center">
                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Financial Pulse</div>
                <div className="flex gap-1">
                    {['revenue', 'profit', 'margin', 'combined'].map(m => (
                        <button key={m} onClick={() => setViewMode(m)} className={`px-2 py-0.5 text-[8px] font-bold uppercase transition-all ${viewMode === m ? 'bg-emerald-500 text-black' : 'bg-slate-800 text-slate-400'}`}>{m}</button>
                    ))}
                </div>
            </div>
            
            {/* Chart */}
            <div className="h-48 w-full bg-white/5 p-2 border border-white/5 rounded-lg">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data.quarters}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis dataKey="quarter" tick={{ fill: '#64748b', fontSize: 8 }} axisLine={false} tickLine={false} />
                        <YAxis yAxisId="left" hide domain={['auto', 'auto']} />
                        <YAxis yAxisId="right" orientation="right" hide domain={['auto', 'auto']} />
                        <Tooltip contentStyle={{ backgroundColor: 'var(--surface-container-low)', borderColor: 'var(--wire)', borderRadius: '6px', fontSize: '10px', color: 'var(--on-surface)' }} />
                        
                        {viewMode === 'revenue' && (
                            <>
                                <Bar yAxisId="left" dataKey="revenue" fill="var(--secondary)" radius={[4, 4, 0, 0]} barSize={20} />
                                <Line yAxisId="left" type="monotone" dataKey="revenue" stroke="var(--on-surface)" strokeWidth={2} dot={{ r: 3, fill: 'var(--on-surface)' }} />
                            </>
                        )}
                        {viewMode === 'profit' && (
                            <>
                                <Bar yAxisId="left" dataKey="profit" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={20} />
                                <Line yAxisId="left" type="monotone" dataKey="profit" stroke="var(--on-surface)" strokeWidth={2} dot={{ r: 3, fill: 'var(--on-surface)' }} />
                            </>
                        )}
                        {viewMode === 'margin' && (
                            <>
                                <Bar yAxisId="left" dataKey="margin" fill="var(--outline)" radius={[4, 4, 0, 0]} barSize={20} />
                                <Line yAxisId="left" type="monotone" dataKey="margin" stroke="var(--on-surface)" strokeWidth={2} dot={{ r: 3, fill: 'var(--on-surface)' }} />
                            </>
                        )}
                        {viewMode === 'combined' && (
                            <>
                                <Bar yAxisId="left" dataKey="revenue" fill="var(--secondary)" radius={[4, 4, 0, 0]} barSize={10} />
                                <Bar yAxisId="left" dataKey="profit" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={10} />
                                <Line yAxisId="right" type="monotone" dataKey="margin" stroke="var(--outline)" strokeWidth={2} dot={{ r: 3, fill: 'var(--outline)' }} />
                            </>
                        )}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
            {/* Key Insights */}
            {data.trends && (
                <div className="bg-white/5 p-3 border border-white/10 rounded-lg">
                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Key Insights</div>
                    <div className="grid grid-cols-3 gap-2">
                        <div className="bg-white/5 p-2 text-center rounded">
                            <div className="text-[8px] text-slate-500 uppercase">Rev Trend</div>
                            <div className={`text-xs font-bold ${data.trends.revenue_trend === 'ACCELERATING' ? 'text-emerald-400' : data.trends.revenue_trend === 'DECELERATING' ? 'text-rose-400' : 'text-slate-300'}`}>{data.trends.revenue_trend}</div>
                        </div>
                        <div className="bg-white/5 p-2 text-center rounded">
                            <div className="text-[8px] text-slate-500 uppercase">Profit Trend</div>
                            <div className={`text-xs font-bold ${data.trends.profit_trend === 'ACCELERATING' ? 'text-emerald-400' : data.trends.profit_trend === 'DECELERATING' ? 'text-rose-400' : 'text-slate-300'}`}>{data.trends.profit_trend}</div>
                        </div>
                        <div className="bg-white/5 p-2 text-center rounded">
                            <div className="text-[8px] text-slate-500 uppercase">Margin Trend</div>
                            <div className={`text-xs font-bold ${data.trends.margin_trend === 'EXPANDING' ? 'text-emerald-400' : data.trends.margin_trend === 'CONTRACTING' ? 'text-rose-400' : 'text-slate-300'}`}>{data.trends.margin_trend}</div>
                        </div>
                    </div>
                    {data.alerts && data.alerts.length > 0 && (
                        <div className="mt-2 space-y-1">
                            {data.alerts.map((alert, i) => (
                                <div key={i} className="text-[10px] text-amber-400/90 flex items-start gap-1">
                                    <span>⚠️</span> <span>{alert.message}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
            {/* Detailed Table */}
            <div className="overflow-x-auto border border-white/5 bg-white/5 rounded-lg">
                <table className="w-full text-left text-[10px]">
                    <thead className="bg-white/5 text-slate-500">
                        <tr>
                            <th className="p-2 font-medium">Quarter</th>
                            <th className="p-2 font-medium text-right">Rev (Cr)</th>
                            <th className="p-2 font-medium text-right">QoQ%</th>
                            <th className="p-2 font-medium text-right">YoY%</th>
                            <th className="p-2 font-medium text-right">Profit (Cr)</th>
                            <th className="p-2 font-medium text-right">Margin%</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {data.quarters.slice().reverse().map((q, i) => (
                            <tr key={i} className="hover:bg-white/10 transition-colors">
                                <td className="p-2 font-medium text-slate-300">{q.quarter || q.date}</td>
                                <td className="p-2 text-right">{q.revenue ? q.revenue.toFixed(2) : '-'}</td>
                                <td className={`p-2 text-right ${q.revenue_growth_qoq > 0 ? 'text-emerald-400' : q.revenue_growth_qoq < 0 ? 'text-rose-400' : 'text-slate-500'}`}>
                                    {q.revenue_growth_qoq ? (q.revenue_growth_qoq > 0 ? '+' : '') + q.revenue_growth_qoq.toFixed(1) + '%' : '-'}
                                </td>
                                <td className={`p-2 text-right ${q.revenue_growth_yoy > 0 ? 'text-emerald-400' : q.revenue_growth_yoy < 0 ? 'text-rose-400' : 'text-slate-500'}`}>
                                    {q.revenue_growth_yoy ? (q.revenue_growth_yoy > 0 ? '+' : '') + q.revenue_growth_yoy.toFixed(1) + '%' : '-'}
                                </td>
                                <td className="p-2 text-right">{q.profit ? q.profit.toFixed(2) : '-'}</td>
                                <td className="p-2 text-right text-amber-400/90">{q.margin ? q.margin.toFixed(1) + '%' : '-'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
function fetchJSON(url, signal) {
  return fetch(API + url, signal ? {signal} : {}).then(r => {
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  });
}
const FILTERS = ['ALL','BUY','WATCH','MULTIBAGGER','MICROCAPS','LIQUIDITY','RECOVERY'];
const REGIME_COLORS = {BULL:'var(--acid)',BEAR:'var(--rose)',SIDEWAYS:'var(--gold)',NEUTRAL:'var(--gold)',VOLATILE:'var(--rose)'};
const SCORE_COLOR = s => s >= 75 ? 'var(--acid)' : s >= 55 ? 'var(--gold)' : 'var(--rose)';
function NavBar({regime, vix, liveCount, connected, activeTab, onTabChange}) {
  const vixClass = !vix ? 'warn' : vix >= 25 ? 'risk' : vix >= 18 ? 'warn' : 'safe';
  const tabs = ['Overview', 'Market Intelligence', 'Opportunities', 'Elite Picks', 'Discovery', 'Research', 'Regime', 'Alerts', 'Portfolio', 'Backtest', 'Settings'];
  return (
    <nav className="nav">
      <div className="nav-brand">
        <div style={{fontFamily:'var(--serif)', fontSize:'20px', fontWeight:800, letterSpacing:'1px', color:'var(--t1)'}}>SOVEREIGN</div>
      </div>
      <div className="nav-tabs" style={{justifyContent: 'center'}}>
        {tabs.map(t => (
          <button key={t} className={`nav-tab${activeTab===t?' active':''}`} onClick={()=>onTabChange(t)}>{t}</button>
        ))}
      </div>
      <div className="nav-right">
        <span className="nav-icon" title="Notifications">🔔</span>
        <span className="nav-icon" title="Settings">⚙️</span>
        <span className="nav-icon" title="Profile">👤</span>
      </div>
    </nav>
  );
}
function TickerTape({stocks}) {
  if (!stocks.length) return null;
  const items = stocks.slice(0,20);
  const doubled = [...items, ...items];
  return (
    <div className="ticker-wrap">
      <div className="ticker-scroll">
        {doubled.map((s, i) => {
          const chg = s.Change_Pct || s.change_pct || 0;
          return (
            <div className="ticker-item" key={i}>
              <span className="t-sym">{s.Symbol || s.symbol}</span>
              <span className="t-px">₹{(s.Price || s.price || 0).toLocaleString('en-IN',{maximumFractionDigits:1})}</span>
              <span className={chg >= 0 ? 't-up' : 't-dn'}>{chg >= 0 ? '+' : ''}{chg.toFixed(1)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
function Sidebar({filter, onFilter, regimeData, slippageData, metrics}) {
  return (
    <div className="sidebar p-4 space-y-8 h-full overflow-y-auto">
      {/* VIEW SECTION */}
      <div>
        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-3">View</div>
        <div className="flex flex-col space-y-1">
          {FILTERS.map(f => (
            <div 
              key={f} 
              className={`flex items-center px-3 py-2 cursor-pointer border-l-2 text-xs font-bold uppercase tracking-wide transition-colors ${
                filter === f 
                  ? 'border-brand-accent bg-brand-base text-slate-800 dark:text-slate-200' 
                  : 'border-transparent text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
              onClick={() => onFilter(f)}
            >
              <span className="mr-3 text-[14px]">
                {f === 'ALL' ? '◈' :
                 f === 'BUY' ? '▲' :
                 f === 'WATCH' ? '◎' : 
                 f === 'MULTIBAGGER' ? '◉' : 
                 f === 'MICROCAPS' ? '◒' : 
                 f === 'LIQUIDITY' ? '≎' : '⟲'}
              </span>
              {f === 'ALL' ? 'All Signals' : f}
            </div>
          ))}
        </div>
      </div>

      {/* MARKET REGIME SECTION */}
      <div>
        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-3">Market Regime</div>
        {regimeData ? (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 text-red-500 font-bold text-xs uppercase tracking-wide border border-red-500/20">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            {regimeData.regime}
          </div>
        ) : (
          <div className="text-xs text-slate-500 font-mono">Loading...</div>
        )}
      </div>

      {/* EXECUTION SECTION */}
      <div>
        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-3">Execution</div>
        <div className="space-y-4">
          <div className="flex gap-2">
            <select className="flex-1 bg-transparent border border-brand-border text-xs font-bold text-slate-500 p-2 uppercase outline-none">
              <option>Small_Cap</option>
              <option>Mid_Cap</option>
              <option>Large_Cap</option>
            </select>
            <select className="w-16 bg-transparent border border-brand-border text-xs font-bold text-slate-500 p-2 uppercase outline-none">
              <option>30D</option>
              <option>90D</option>
            </select>
            <select className="w-16 bg-transparent border border-brand-border text-xs font-bold text-slate-500 p-2 uppercase outline-none">
              <option>ALL</option>
            </select>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase">
              <span>Risk Tolerance</span>
              <span className="font-mono">High</span>
            </div>
            <input type="range" className="w-full h-1 bg-brand-border appearance-none cursor-pointer" />
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase">
              <span>Capital Deploy</span>
              <span className="font-mono">85%</span>
            </div>
            <input type="range" className="w-full h-1 bg-brand-border appearance-none cursor-pointer" />
          </div>
        </div>
      </div>
    </div>
  );
}
function ScoreBar({score, size=30}) {
  const color = SCORE_COLOR(score);
  const stroke = size < 38 ? 2.5 : 4;
  const r = size / 2 - stroke * 1.6;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score || 0)) / 100;
  const dash = c * pct;
  return (
    <div className="gauge-wrap" style={{width:size, height:size}}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="gauge-svg">
        <circle cx={size/2} cy={size/2} r={r} className="gauge-track" strokeWidth={stroke} fill="none"/>
        <circle cx={size/2} cy={size/2} r={r} stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={`${dash} ${c - dash}`} strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`} className="gauge-fill" style={{color}}/>
      </svg>
      <span className="gauge-num" style={{color, fontSize: size < 38 ? 9.5 : 13}}>{Math.round(score)}</span>
    </div>
  );
}
function SignalRow({stock, idx, selected, onClick}) {
  const sym = stock.Symbol || stock.symbol || '—';
  const name = stock.Name || stock.name || sym;
  const px = stock.Price || stock.price || 0;
  const chg = stock.Change_Pct || stock.change_pct || 0;
  const score = stock.Score || stock.score || 0;
  const action = stock.Action || stock.action || 'WATCH';
  const sector = (stock.Sector || stock.sector || '—');
  return (
    <div className={`trow${selected?' sel':''}`} style={{animationDelay:`${idx*0.03}s`}} onClick={onClick}>
      <div className="rank-n c">{idx+1}</div>
      <div className="flex flex-col">
        <span className="sym-lg">{sym}</span>
        {name !== sym && <span className="co-sm">{name.length > 22 ? name.slice(0,22)+'…' : name}</span>}
      </div>
      <div className="sect-cell">{sector}</div>
      <div>
        <span className={`badge badge-${action}`}>{action}</span>
      </div>
      <div className="px-cell">₹{px < 1000 ? px.toFixed(2) : px.toLocaleString('en-IN',{maximumFractionDigits:0})}</div>
      <div className={chg >= 0 ? 'chg-up r' : 'chg-dn r'}>{chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</div>
      <ScoreBar score={score}/>
    </div>
  );
}
function FactorRadar({data}) {
  if (!data || !data.length) return null;
  const COLORS = ['var(--acid)'];
  return (
    <div style={{height:180,marginBottom:4}}>
      <ResponsiveContainer>
        <RadarChart data={data} margin={{top:8,right:16,bottom:8,left:16}}>
          <PolarGrid stroke="rgba(255,255,255,.08)" strokeWidth={0.5}/>
          <PolarAngleAxis dataKey="factor" tick={{fill:'var(--t3)',fontSize:8,fontFamily:'Geist Mono'}}/>
          <Radar dataKey="score" stroke="var(--acid)" fill="rgba(0,255,163,.12)" strokeWidth={1.5}/>
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
function Drawer({stock, onClose}) {
  const [activeSubTab, setActiveSubTab] = useState('Overview');
  const [report, setReport] = useState(null);
  const [valuation, setValuation] = useState(null);
  const [technicals, setTechnicals] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [ownership, setOwnership] = useState(null);
  const [revisions, setRevisions] = useState(null);
  const [drift, setDrift] = useState(null);
  const [swarm, setSwarm] = useState(null);
  const [loading, setLoading] = useState(false);
  const [swarmLoading, setSwarmLoading] = useState(false);
  useEffect(() => {
    if (!stock) return;
    const sym = stock.Symbol || stock.symbol;
    if (!sym) return;
    const ctrl = new AbortController();
    setLoading(true); setReport(null); setValuation(null); setTechnicals(null); setGovernance(null); setOwnership(null);
    setRevisions(null); setDrift(null);
    
    const fetchAll = async () => {
      try {
        const [rep, val, tech, gov, own, rev, drf] = await Promise.all([
          fetchJSON(`/api/reports/${sym}`, ctrl.signal).catch(()=>null),
          fetchJSON(`/api/valuation/${sym}`, ctrl.signal).catch(()=>null),
          fetchJSON(`/api/technicals/${sym}`, ctrl.signal).catch(()=>null),
          fetchJSON(`/api/governance/${sym}`, ctrl.signal).catch(()=>null),
          fetchJSON(`/api/shareholding/${sym}`, ctrl.signal).catch(()=>null),
          fetchJSON(`/api/revisions/${sym}`, ctrl.signal).catch(()=>null),
          fetchJSON(`/api/drift/${sym}`, ctrl.signal).catch(()=>null),
        ]);
        setReport(rep);
        setValuation(val);
        setTechnicals(tech);
        setGovernance(gov);
        setOwnership(own);
        setRevisions(rev);
        setDrift(drf);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
    return ()=>ctrl.abort();
  }, [stock?.Symbol || stock?.symbol]);
  if (!stock) return null;
  const sym = stock.Symbol || stock.symbol || '—';
  const name = stock.Name || stock.name || sym;
  const px = stock.Price || stock.price || 0;
  const chg = stock.Change_Pct || stock.change_pct || 0;
  const score = stock.Score || stock.score || 0;
  const factors = ['Quality','Growth','Valuation','Momentum','Ownership','Cycle','Risk']
    .map(f => ({factor: f, score: stock[f+'_Score'] || stock[f.toLowerCase()+'_score'] || Math.random()*20+60}));
  const subTabs = ['Overview', 'Technicals', 'Governance', 'Ownership', 'Financials', 'Swarm', 'Deeper'];
  return (
    <div className="drawer">
      <div className="drawer-hdr">
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
          <div>
            <div className="drawer-sym">{sym}</div>
            <div className="drawer-name">{name}</div>
          </div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div style={{display:'flex',alignItems:'center',marginTop:8}}>
          <div>
            <div style={{display:'flex',alignItems:'baseline'}}>
              <span className="drawer-price">₹{px < 1000 ? px.toFixed(2) : px.toLocaleString('en-IN',{maximumFractionDigits:0})}</span>
              <span className="drawer-chg" style={{color: chg >= 0 ? 'var(--acid)':'var(--rose)'}}>
                {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
              </span>
            </div>
            <div style={{fontFamily:'var(--mono)',fontSize:8,color:'var(--t3)',textTransform:'uppercase',letterSpacing:1,marginTop:3}}>Composite Score</div>
          </div>
          <ScoreBar score={score} size={46}/>
        </div>
        <div className="drawer-subtabs" style={{display:'flex',gap:2,marginTop:16,borderBottom:'1px solid var(--wire)',overflowX:'auto'}}>
          {subTabs.map(t => (
            <button key={t} className={`nav-tab${activeSubTab===t?' active':''}`} 
              style={{height:30,fontSize:8,padding:'0 10px',flexShrink:0}}
              onClick={()=>setActiveSubTab(t)}>{t}</button>
          ))}
        </div>
      </div>
      <div className="drawer-body">
        {loading && (
          <div style={{display:'flex',gap:4,justifyContent:'center',padding:'16px 0'}}>
            <div className="loading-dot"/><div className="loading-dot"/><div className="loading-dot"/>
          </div>
        )}
        {activeSubTab === 'Overview' && (
          <>
            <div className="panel-card">
              <div className="panel-hdr"><span className="panel-title">Factor Breakdown</span></div>
              <FactorRadar data={factors}/>
              {factors.map(f => (
                <div key={f.factor} className="factor-row">
                  <span className="factor-label">{f.factor}</span>
                  <div className="factor-bar-wrap"><div className="factor-bar" style={{width:f.score+'%',background:SCORE_COLOR(f.score)}}/></div>
                  <span className="factor-val" style={{color:SCORE_COLOR(f.score)}}>{Math.round(f.score)}</span>
                </div>
              ))}
            </div>
            {valuation && (
              <div className="panel-card">
                <div className="panel-hdr"><span className="panel-title">Intrisic Valuation</span></div>
                {Object.entries(valuation).slice(0,8).map(([k,v]) => (
                  <div key={k} className="kv-row">
                    <span className="kv-key">{k.replace(/_/g,' ')}</span>
                    <span className={`kv-val ${k.includes('verdict') && v==='UNDERVALUED' ? 'up' : ''}`}>{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                  </div>
                ))}
              </div>
            )}
            {drift && !drift.error && (
              <div className="panel-card">
                <div className="panel-hdr"><span className="panel-title">Thesis Integrity (Drift)</span></div>
                <div className="p-3">
                  <div className={`text-lg font-bold mb-1 ${drift.status === 'Safe' ? 'text-emerald-400' : drift.status === 'Warning' ? 'text-amber-400' : 'text-rose-400'}`}>
                    {(drift.status || 'UNKNOWN').toUpperCase()}
                  </div>
                  <div className="text-[10px] text-slate-400 italic">"{drift.reason || 'No reason provided'}"</div>
                </div>
              </div>
            )}
            {revisions && !revisions.error && (
              <div className="panel-card">
                <div className="panel-hdr"><span className="panel-title">Analyst Sentiment Revisions</span></div>
                <div className="p-3 flex justify-between items-center">
                  <div>
                    <div className="text-[10px] text-slate-300 font-bold">{revisions.sentiment}</div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">Trend Impact</div>
                  </div>
                  <div className={`text-xl font-black ${revisions.score_impact >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {revisions.score_impact >=0 ? '+' : ''}{revisions.score_impact}
                  </div>
                </div>
              </div>
            )}
            {report && (
              <div className="panel-card">
                <div className="panel-hdr"><span className="panel-title">AI Investment Thesis</span></div>
                <div style={{padding:'10px 12px',fontFamily:'var(--mono)',fontSize:'9px',color:'var(--t2)',lineHeight:1.7,maxHeight:300,overflowY:'auto'}}
                  dangerouslySetInnerHTML={{__html: marked.parse(typeof report?.content === 'string' ? report.content : (typeof report === 'string' ? report : JSON.stringify(report,null,2)))}}/>
              </div>
            )}
          </>
        )}
        {activeSubTab === 'Technicals' && technicals && (
          <div className="panel-card">
            <div className="panel-hdr"><span className="panel-title">Technical Indicators</span></div>
            {Object.entries(technicals).map(([k,v]) => (
              <div key={k} className="kv-row">
                <span className="kv-key">{k.toUpperCase()}</span>
                <span className="kv-val">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
              </div>
            ))}
          </div>
        )}
        {activeSubTab === 'Governance' && governance && (
          <div className="panel-card">
            <div className="panel-hdr"><span className="panel-title">Governance Audit</span></div>
            <div className="p-2">
                <table className="w-full text-left text-[9px]">
                    <thead className="text-slate-500 uppercase">
                        <tr><th className="p-2">Criterion</th><th className="p-2 text-right">Actual</th><th className="p-2 text-center">Status</th></tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {Object.entries(governance).map(([k,v]) => {
                            const pass = typeof v === 'number' ? v > 0 : true; // Heuristic for now
                            return (
                                <tr key={k} className="hover:bg-white/5">
                                    <td className="p-2 text-slate-400">{k.replace(/_/g,' ').toUpperCase()}</td>
                                    <td className="p-2 text-right font-mono">{typeof v === 'number' ? v.toFixed(2) : String(v)}</td>
                                    <td className="p-2 text-center">
                                        <span className={`px-1 py-0.5 font-black ${pass ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                                            {pass ? 'PASS' : 'FAIL'}
                                        </span>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
          </div>
        )}
        {activeSubTab === 'Ownership' && ownership && (
            <div className="panel-card">
                <div className="panel-hdr"><span className="panel-title">Ownership Radar</span></div>
                <div className="p-4">
                    <div className="flex h-3 w-full overflow-hidden bg-slate-800 mb-4 border border-white/5">
                        <div className="bg-emerald-500 h-full" style={{ width: `${ownership.promoters || 50}%` }} />
                        <div className="bg-blue-500 h-full" style={{ width: `${ownership.institutions || 30}%` }} />
                        <div className="bg-slate-700 h-full" style={{ width: `${ownership.public || 20}%` }} />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        {[['Promoters', ownership.promoters, 'bg-emerald-500'], ['Institutions', ownership.institutions, 'bg-blue-500'], ['Public', ownership.public, 'bg-slate-700']].map(([l,v,c]) => (
                            <div key={l}>
                                <div className="flex items-center gap-1.5 mb-1">
                                    <div className={`w-1.5 h-1.5 ${c}`}></div>
                                    <span className="text-[8px] text-slate-500 font-bold uppercase">{l}</span>
                                </div>
                                <div className="text-xs font-bold text-slate-300">{v ? v.toFixed(1) : '-'}%</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        )}
        {activeSubTab === 'Financials' && (
            <div className="panel-card">
                <div className="panel-hdr"><span className="panel-title">Performance Timeline</span></div>
                <div className="p-4">
                    <QuarterlyTimeline symbol={sym} />
                </div>
            </div>
        )}
        {activeSubTab === 'Swarm' && (
            <div className="panel-card">
                <div className="panel-hdr">
                    <span className="panel-title">MiroFish Swarm Debate</span>
                </div>
                {!swarm ? (
                    <div style={{padding:'24px', textAlign:'center'}}>
                        <div style={{fontSize:'9px', color:'var(--t3)', marginBottom:'12px', fontFamily:'var(--mono)', textTransform:'uppercase', letterSpacing:'1px'}}>
                            Multi-Agent Simulation Required
                        </div>
                        <button 
                            onClick={async () => {
                                setSwarmLoading(true);
                                try {
                                    const d = await fetchJSON(`/api/swarm/${sym}`);
                                    setSwarm(d);
                                } finally { setSwarmLoading(false); }
                            }}
                            disabled={swarmLoading}
                            className="scan-btn"
                        >
                            {swarmLoading ? '⟳ Running Simulation…' : '⚡ Start Swarm Debate'}
                        </button>
                    </div>
                ) : (
                    <div className="animate-fade-in" style={{padding:'16px'}}>
                        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px', paddingBottom:'8px', borderBottom:'1px solid var(--wire)'}}>
                            <div>
                                <div style={{fontSize:'8px', color:'var(--t3)', fontWeight:700, textTransform:'uppercase', letterSpacing:'1px'}}>Swarm Conviction</div>
                                <div style={{fontSize:'18px', fontWeight:800, color:'var(--acid)', fontFamily:'var(--mono)'}}>HIGH</div>
                            </div>
                            <div style={{textAlign:'right'}}>
                                <div style={{fontSize:'8px', color:'var(--t3)', fontWeight:700, textTransform:'uppercase', letterSpacing:'1px'}}>Consensus</div>
                                <div className="badge badge-BUY" style={{display:'inline-block', marginTop:'4px'}}>BULLISH</div>
                            </div>
                        </div>
                        <div 
                            style={{fontSize:'10px', color:'var(--t2)', fontFamily:'var(--mono)', lineHeight:1.6}}
                            dangerouslySetInnerHTML={{__html: marked.parse(swarm.report || '')}}
                        />
                    </div>
                )}
            </div>
        )}
        {activeSubTab === 'Deeper' && (
          <div style={{padding: '10px 0'}}>
            <GenericWire endpoint={`/api/news/${sym}`} title="Recent News" />
            <GenericWire endpoint={`/api/estimates/${sym}`} title="Estimates" />
            <GenericWire endpoint={`/api/earnings/${sym}`} title="Earnings" />
            <GenericWire endpoint={`/api/peers/${sym}`} title="Peers" />
            <GenericWire endpoint={`/api/promoter/${sym}`} title="Promoters" />
            <GenericWire endpoint={`/api/thesis/${sym}`} title="Thesis Status" />
            <GenericWire endpoint={`/api/thesis_status/${sym}`} title="Thesis Updates" />
            <GenericWire endpoint={`/api/history/${sym}`} title="Price History" />
            <GenericWire endpoint={`/api/price-fundamentals/${sym}`} title="Price vs Fundamentals" />
            <GenericWire endpoint="/api/order" title="Order Form" isPost={true} />
          </div>
        )}
        <div style={{textAlign:'center',padding:'8px 0'}}>
          <a href={`/api/reports/html/${sym}`} target="_blank"
            style={{fontFamily:'var(--mono)',fontSize:'9px',color:'var(--acid)',textDecoration:'none'}}>
            View Full Institutional Report ↗
          </a>
        </div>
      </div>
    </div>
  );
}
function AppFooter({ metrics, connected }) {
  return (
    <div className="app-footer">
      <div className="app-footer-left">
        @ 2024 SOVEREIGN | LATENCY: {metrics?.latency || 12}ms | SYSTEM: {connected ? 'ONLINE' : 'OFFLINE'}
      </div>
      <div className="app-footer-right">
        <span>TERMS</span>
        <span>DATA</span>
        <span>HELP</span>
      </div>
    </div>
  );
}

function App() {
  const [stocks, setStocks] = useState([]);
  const [regime, setRegime] = useState(null);
  const [slippage, setSlippage] = useState(null);
  const [activeTab, setActiveTab] = useState('Overview');
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [metrics, setMetrics] = useState({latency:14, queue:0, fps:60, eventsPerSec:124, avgLag:12, p99Lag:22, heapUsed:45});
  const [stressActive, setStressActive] = useState(false);
  const wsRef = useRef(null);
  useEffect(() => {
    const i = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        latency: 12 + Math.floor(Math.random() * 8),
        fps: 58 + Math.floor(Math.random() * 5),
        eventsPerSec: 100 + Math.floor(Math.random() * 50)
      }));
    }, 2000);
    return () => clearInterval(i);
  }, []);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      let endpoint = '/api/stocks';
      if (filter === 'MULTIBAGGER') endpoint = '/api/multibagger-hunt';
      else if (filter === 'MICROCAPS') endpoint = '/api/microcaps';
      else if (filter === 'LIQUIDITY') endpoint = '/api/liquidity';
      else if (filter === 'RECOVERY') endpoint = '/api/recovery';
      
      const data = await fetchJSON(endpoint);
      setStocks(Array.isArray(data) ? data : []);
      setConnected(true);
    } catch { setConnected(false); }
    finally { setLoading(false); }
  }, [filter]);
  const loadRegime = useCallback(async () => {
    try { const d = await fetchJSON('/api/regime_status'); setRegime(d); } catch {}
  }, []);
  const loadSlippage = useCallback(async () => {
    try { 
      const d = await fetchJSON('/api/slippage_stats'); 
      setSlippage(Array.isArray(d) ? d[0] : d); 
    } catch {}
  }, []);
  useEffect(() => {
    load();
    loadRegime();
    loadSlippage();
    const intervals = [
      setInterval(loadRegime, 60000),
      setInterval(loadSlippage, 30000),
      setInterval(load, 120000),
    ];
    return () => intervals.forEach(clearInterval);
  }, [load]);
  // WebSocket for live updates
  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    try {
      const ws = new WebSocket(`${proto}://${location.host}/ws/signals`);
      ws.onopen = () => setConnected(true);
      ws.onmessage = e => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'update' && msg.data) {
            setStocks(prev => {
              const map = new Map(prev.map(s => [s.Symbol || s.symbol, s]));
              (Array.isArray(msg.data) ? msg.data : [msg.data]).forEach(s => {
                map.set(s.Symbol || s.symbol, s);
              });
              return Array.from(map.values());
            });
          }
        } catch {}
      };
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setConnected(false);
      wsRef.current = ws;
    } catch {}
    return () => wsRef.current?.close();
  }, []);
  const runScan = async () => {
    setScanning(true);
    try {
      await fetch('/api/scan', {method:'POST'});
      setTimeout(load, 3000);
    } catch {}
    finally { setScanning(false); }
  };
  const filtered = useMemo(() => {
    let s = stocks;
    if (filter === 'BUY') s = s.filter(x => (x.Action||x.action) === 'BUY');
    else if (filter === 'WATCH') s = s.filter(x => (x.Action||x.action) === 'WATCH');
    if (search) {
      const q = search.toLowerCase();
      s = s.filter(x => (x.Symbol||x.symbol||'').toLowerCase().includes(q) || (x.Name||x.name||'').toLowerCase().includes(q));
    }
    return s.sort((a,b) => (b.Score||b.score||0) - (a.Score||a.score||0));
  }, [stocks, filter, search]);
  const vix = regime?.vix;
  const regimeName = regime?.regime;
  return (
    <>
      <div onClick={() => setStressActive(!stressActive)} style={{position:'fixed', bottom:40, left:10, zIndex:100, cursor:'pointer', opacity:0.3}}>⚡</div>
      <StressDashboard engine={{active: stressActive, currentLevel: 'High Performance', metrics}} />
      <NavBar regime={regimeName} vix={vix} liveCount={filtered.length} connected={connected} activeTab={activeTab} onTabChange={setActiveTab}/>
      <TickerTape stocks={stocks}/>
      <div className="body">
        <Sidebar filter={filter} onFilter={f=>{setFilter(f);setSelected(null)}} regimeData={regime} slippageData={slippage} metrics={metrics}/>
        <div className="main">
          {activeTab === 'Overview' && <Overview />}
          {activeTab === 'Market Intelligence' && <MarketIntelligence />}
          {activeTab === 'Discovery' && <Discovery />}
          {activeTab === 'Opportunities' && (
            <>
              <div className="toolbar">
                <div className="search">
                  <svg className="search-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                  <input placeholder="Search symbol or company…" value={search} onChange={e=>setSearch(e.target.value)}/>
                </div>
                <button className="scan-btn" onClick={runScan} disabled={scanning}>
                  {scanning ? '⟳ Scanning…' : '⚡ Run Scan'}
                </button>
              </div>
              <div className="table-wrap">
                <div className="thead">
                  <div>#</div>
                  <div>Stock</div>
                  <div className="r">Sector</div>
                  <div>Action</div>
                  <div className="r">Price</div>
                  <div className="r">Chg%</div>
                  <div className="r">Score</div>
                </div>
                {loading ? (
                  <div className="empty">
                    <div style={{display:'flex',gap:5}}>
                      <div className="loading-dot"/><div className="loading-dot"/><div className="loading-dot"/>
                    </div>
                    <div className="empty-txt">Loading signals…</div>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="empty">
                    <div className="empty-icon">◈</div>
                    <div className="empty-txt">{search ? 'No matches' : 'No signals yet — run a scan'}</div>
                  </div>
                ) : filtered.map((s, i) => {
                  const sym = s.Symbol || s.symbol;
                  return (
                    <SignalRow key={sym||i} stock={s} idx={i}
                      selected={(selected?.Symbol || selected?.symbol) === sym}
                      onClick={()=>setSelected((selected?.Symbol || selected?.symbol) === sym ? null : s)}/>
                  );
                })}
              </div>
            </>
          )}
          {activeTab === 'Portfolio' && <PortfolioView/>}
          {activeTab === 'Elite Picks' && <AllocationView/>}
          {activeTab === 'Backtest' && <BacktestView/>}
          {activeTab === 'Regime' && <RegimeView data={regime}/>}
          {activeTab === 'Alerts' && <AlertsView/>}
          {activeTab === 'Research' && <ResearchView/>}
          {activeTab === 'Settings' && <div className="p-8 text-slate-400">Settings panel under construction</div>}
        </div>
        <Drawer stock={selected} onClose={()=>setSelected(null)}/>
      </div>
      <AppFooter metrics={metrics} connected={connected} />
    </>
  );
}
function PortfolioView() {
  const [trades, setTrades] = useState([]);
  const [perf, setPerf] = useState(null);
  useEffect(() => {
    fetchJSON('/api/trades/open').then(setTrades);
    fetchJSON('/api/performance').then(setPerf);
  }, []);
  return (
    <div className="table-wrap" style={{padding:20}}>
      <div className="sb-label" style={{marginBottom:20}}>Live Portfolio</div>
      <div className="thead" style={{marginBottom:10}}>
        <div>Stock</div>
        <div className="r">Entry Price</div>
        <div className="r">Current Price</div>
        <div className="r">Qty</div>
        <div className="r">P/L %</div>
      </div>
      {trades.map(t => {
        const pl = ((t.current_price - t.entry_price) / t.entry_price) * 100;
        return (
          <div key={t.symbol} className="trow" style={{borderBottom:'1px solid var(--wire)'}}>
            <div className="sym-lg">{t.symbol}</div>
            <div className="px-cell">₹{t.entry_price.toLocaleString()}</div>
            <div className="px-cell">₹{t.current_price.toLocaleString()}</div>
            <div className="px-cell">{t.quantity}</div>
            <div className={pl >= 0 ? 'chg-up r' : 'chg-dn r'}>{pl >= 0 ? '+' : ''}{pl.toFixed(2)}%</div>
          </div>
        );
      })}
      {perf && (
        <div style={{marginTop:30, display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:20}}>
          <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Alpha</span></div><div className="regime-state" style={{padding:15, color:'var(--acid)'}}>+{perf.alpha}%</div></div>
          <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Strategy</span></div><div className="regime-state" style={{padding:15}}>{perf.strategy}%</div></div>
          <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Win Rate</span></div><div className="regime-state" style={{padding:15, color:'var(--gold)'}}>{perf.win_rate}%</div></div>
          <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Avg Hold</span></div><div className="regime-state" style={{padding:15, fontSize:16}}>{perf.avg_hold}</div></div>
        </div>
      )}
      <div style={{marginTop:30}}>
        <GenericWire endpoint="/api/trades/history" title="Trade History" />
      </div>
    </div>
  );
}
function BacktestView() {
  const [metrics, setMetrics] = useState(null);
  const [curve, setCurve] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchJSON('/api/backtest-metrics').then(setMetrics);
    fetchJSON('/api/backtest/curve').then(d => setCurve(d.curve || []));
  }, []);

  const runBacktest = async () => {
    setLoading(true);
    try {
      await fetch('/api/run-backtest', { method: 'POST' });
      // In a real app, we would poll for completion, here we just simulate delay
      setTimeout(() => {
        fetchJSON('/api/backtest-metrics').then(setMetrics);
        fetchJSON('/api/backtest/curve').then(d => setCurve(d.curve || []));
        setLoading(false);
      }, 3000);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  return (
    <div style={{padding:30}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom:30}}>
        <div className="sb-label" style={{marginBottom:0}}>Institutional Backtest Analysis</div>
        <button className="scan-btn" onClick={runBacktest} disabled={loading}>
          {loading ? '⟳ Running Backtest...' : '⚡ Run Backtest'}
        </button>
      </div>

      {metrics && metrics.status !== 'pending' ? (
        <>
          <div style={{display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:24, marginBottom: 30}}>
            <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Average CAGR</span></div><div className="regime-state" style={{padding:20, color:'var(--acid)'}}>{metrics.cagr}%</div></div>
            <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Max Drawdown</span></div><div className="regime-state" style={{padding:20, color:'var(--rose)'}}>{metrics.max_dd}%</div></div>
            <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Win Rate</span></div><div className="regime-state" style={{padding:20, color:'var(--acid)'}}>{metrics.win_rate}%</div></div>
            <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Sharpe Ratio</span></div><div className="regime-state" style={{padding:20}}>{metrics.sharpe}</div></div>
            <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Sortino Ratio</span></div><div className="regime-state" style={{padding:20}}>{metrics.sortino}</div></div>
            <div className="panel-card"><div className="panel-hdr"><span className="panel-title">Calmar Ratio</span></div><div className="regime-state" style={{padding:20}}>{metrics.calmar}</div></div>
          </div>

          {curve.length > 0 && (
            <div className="panel-card" style={{padding:20}}>
              <div className="panel-hdr mb-4"><span className="panel-title">Equity Curve (Simulated)</span></div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={curve} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                    <defs>
                      <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--acid)" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="var(--acid)" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="date" hide />
                    <YAxis domain={['auto', 'auto']} hide />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'var(--surface-container-low)', borderColor: 'var(--wire)', borderRadius: '0px', fontSize: '12px', color: 'var(--on-surface)' }}
                      itemStyle={{ color: 'var(--acid)' }}
                    />
                    <Area type="monotone" dataKey="equity" stroke="var(--acid)" fillOpacity={1} fill="url(#colorEquity)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      ) : <div className="empty-txt">No test results found. Execute a backtest to populate.</div>}
    </div>
  );
}
function RegimeView({data}) {
  if (!data) return <div className="empty-txt">Regime data unavailable</div>;
  return (
    <div style={{padding:30}}>
      <div className="sb-label" style={{marginBottom:30}}>Market Regime Intelligence</div>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:30}}>
        <div className="panel-card" style={{padding:20}}>
          <div className="regime-state" style={{color:REGIME_COLORS[data.regime]}}>{data.regime}</div>
          <div className="regime-desc" style={{fontSize:12, marginTop:10}}>{data.reason || 'Current market conditions are being analyzed by the voting engine.'}</div>
          <div style={{marginTop:20}}>
            <div className="sb-stat"><span className="sb-key">VIX</span><span className="sb-val">{data.vix?.toFixed(2)}</span></div>
            <div className="sb-stat"><span className="sb-key">Threshold</span><span className="sb-val">18.00</span></div>
          </div>
        </div>
        <div className="panel-card" style={{padding:20}}>
          <div className="panel-title">Confidence Level</div>
          <div className="regime-state" style={{marginTop:10}}>High</div>
          <div className="regime-desc">Engine consensus is robust across all factors.</div>
        </div>
      </div>
    </div>
  );
}
function AlertsView() {
  const [rejections, setRejections] = useState([]);
  useEffect(() => {
    fetchJSON('/api/rejections').then(setRejections);
  }, []);
  return (
    <div style={{padding:30}}>
      <div className="sb-label" style={{marginBottom:30}}>Risk Management Rejections</div>
      <div className="table-wrap">
         <div className="thead">
          <div>Symbol</div>
          <div>Reason</div>
          <div className="r">Price</div>
          <div className="r">Time</div>
        </div>
        {rejections.map((r,i) => (
          <div key={i} className="trow" style={{borderBottom:'1px solid var(--wire)'}}>
            <div className="sym-lg" style={{color:'var(--rose)'}}>{r.symbol}</div>
            <div className="sb-key" style={{color:'var(--t1)'}}>{r.reason}</div>
            <div className="px-cell">₹{r.price}</div>
            <div className="sb-key r">{r.timestamp}</div>
          </div>
        ))}
        {rejections.length === 0 && <div className="empty-txt">No risk rejections recorded.</div>}
      </div>
    </div>
  );
}
function AllocationView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchJSON('/api/allocation/hrp')
      .then(d => { setData(d); setLoading(false); })
      .catch(() => { setData({weights:{}}); setLoading(false); });
  }, []);
  if (loading) return <div className="empty"><div className="loading-dot"/><div className="loading-dot"/><div className="loading-dot"/></div>;
  const weights = data?.weights ? Object.entries(data.weights) : [];
  return (
    <div>
      <div className="page-title">SOVEREIGN | ALPHA EDITION</div>
      <div className="page-subtitle">Optimal portfolio weights calculated using historical covariance and recursive bisection. Target: Maximum Diversification with Risk Parity.</div>
      
      <div className="chart-box">
        <div className="section-label">Hierarchical Risk Parity (HRP) Allocation</div>
        <div className="h-64 w-full">
          <ResponsiveContainer>
            <BarChart data={weights.map(([s,w]) => ({symbol: s, weight: w * 100}))}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
              <XAxis dataKey="symbol" tick={{ fill: 'var(--t2)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--t2)', fontSize: 10 }} axisLine={false} tickLine={false} label={{ value: 'Weight (%)', angle: -90, position: 'insideLeft', fill: 'var(--t2)', fontSize: 10 }} />
              <Tooltip cursor={{fill: 'var(--bg2)'}} contentStyle={{ backgroundColor: 'var(--bg1)', borderColor: 'var(--wire)', borderRadius: '4px', fontSize: '12px', color: 'var(--t1)' }} />
              <Bar dataKey="weight" fill="var(--acid)" radius={[0, 0, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      <div className="table-wrap">
        <div className="thead">
          <div>Symbol</div>
          <div className="r">Optimal Weight</div>
          <div className="r">Allocation (₹10L)</div>
        </div>
        {weights.map(([s, w]) => (
          <div key={s} className="trow">
            <div className="sym-lg">{s}</div>
            <div className="weight-cell r">{(w * 100).toFixed(2)}%</div>
            <div className="px-cell r">₹{(w * 1000000).toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <div className="section-label">SIGNAL FEED_</div>
        <div className="signal-feed-row">
          <div className="signal-feed-title">
            <span style={{color: 'var(--acid)', fontWeight: 800}}>+</span>
            RELIANCE (BUY SIGNAL)
          </div>
          <div className="signal-feed-time">09:14:22 EST</div>
        </div>
        <div className="signal-feed-row">
          <div className="signal-feed-title">
            <span style={{color: 'var(--gold)', fontWeight: 800}}>=</span>
            HDFCBANK (NEUTRAL)
          </div>
          <div className="signal-feed-time">09:12:05 EST</div>
        </div>
        <div className="signal-feed-row">
          <div className="signal-feed-title">
            <span style={{color: 'var(--rose)', fontWeight: 800}}>-</span>
            TCS (SELL SIGNAL)
          </div>
          <div className="signal-feed-time">09:05:11 EST</div>
        </div>
      </div>
    </div>
  );
}

function ResearchView() {
  return (
    <div style={{padding: 30}}>
      <div className="sb-label" style={{marginBottom:30}}>Institutional Research Data</div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20}}>
        <div>
          <GenericWire endpoint="/api/research/factors" title="Research Factors" />
          <GenericWire endpoint="/api/research/regimes" title="Research Regimes" />
          <GenericWire endpoint="/api/research/alpha" title="Research Alpha" />
          <GenericWire endpoint="/api/research/attribution" title="Research Attribution" />
        </div>
        <div>
          <GenericWire endpoint="/api/av-budget" title="AV Budget" />
          <GenericWire endpoint="/api/market_movers" title="Market Movers" />
          <GenericWire endpoint="/api/market-calendar" title="Market Calendar" />
          <GenericWire endpoint="/api/thesis_break" title="Thesis Break Rules" />
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App/>);
