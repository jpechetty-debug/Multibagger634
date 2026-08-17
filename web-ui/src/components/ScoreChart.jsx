import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export default function ScoreChart({ data }) {
  // Assume data is an array of objects: { date: '...', score: 90, price: 150 }
  // or if it's just numbers, we map it.
  const chartData = data.map((val, i) => {
    return typeof val === 'object' ? val : { index: i, score: val };
  });

  return (
    <div className="w-full h-32">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis dataKey="index" hide />
          <YAxis stroke="#94a3b8" fontSize={10} tickFormatter={(val) => Math.round(val)} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
            itemStyle={{ color: '#38bdf8' }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={{ r: 3, fill: '#38bdf8', strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
