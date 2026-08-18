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
          <CartesianGrid strokeDasharray="3 3" stroke="var(--wire)" vertical={false} />
          <XAxis dataKey="index" hide />
          <YAxis stroke="var(--outline)" fontSize={10} tickFormatter={(val) => Math.round(val)} />
          <Tooltip
            contentStyle={{ backgroundColor: 'var(--surface-container-low)', borderColor: 'var(--wire)', fontSize: '12px', borderRadius: '6px' }}
            itemStyle={{ color: 'var(--primary)' }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="var(--primary)"
            strokeWidth={2}
            dot={{ r: 3, fill: 'var(--primary)', strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
