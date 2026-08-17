import React, { useState, useEffect } from 'react';

export function GenericWire({ endpoint, title, isPost = false }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isPost && endpoint) {
      setLoading(true);
      fetch(endpoint).then(r => r.json()).then(d => {
        setData(d);
        setLoading(false);
      }).catch(e => {
        setData({ error: String(e) });
        setLoading(false);
      });
    }
  }, [endpoint, isPost]);

  const doAction = () => {
    setLoading(true);
    fetch(endpoint, { method: 'POST' }).then(r => r.json()).then(d => {
      setData(d);
      setLoading(false);
    }).catch(e => {
      setData({ error: String(e) });
      setLoading(false);
    });
  }

  return (
    <div className="panel-card" style={{ marginBottom: 10 }}>
      <div className="panel-hdr" style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <span className="panel-title">{title || endpoint}</span>
        {isPost && <button onClick={doAction} className="scan-btn" style={{padding:'2px 8px', fontSize:'8px'}}>Execute</button>}
      </div>
      <div style={{padding:'8px', overflow:'auto', maxHeight:200}}>
        {loading ? <div style={{fontSize:'10px', color:'var(--t3)'}}>Loading...</div> : 
         data ? <pre style={{fontSize:'8px', color:'var(--t2)', fontFamily:'var(--mono)', margin:0, whiteSpace:'pre-wrap'}}>{JSON.stringify(data, null, 2)}</pre> : 
         <div style={{fontSize:'10px', color:'var(--t3)'}}>No Data</div>}
      </div>
    </div>
  );
}
