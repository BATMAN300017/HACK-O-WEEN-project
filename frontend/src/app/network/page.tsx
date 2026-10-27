'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';

export default function NetworkPage() {
  const [paths, setPaths] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any[]>('/graph/suspicious-paths');
        setPaths(res || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Network Intelligence</h1>
      <p className="text-slate-500 text-sm">Discovered topological structures, fan-in hubs, and intermediary forwarding.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {paths.map((p, idx) => (
          <div key={idx} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2 text-xs">
            <div className="font-bold text-sky-800 text-sm">{p.pattern_name}</div>
            <div className="text-slate-700">{p.explanation}</div>
            <div className="text-slate-400 italic">Alternative hypothesis: {p.alternative_explanations}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
