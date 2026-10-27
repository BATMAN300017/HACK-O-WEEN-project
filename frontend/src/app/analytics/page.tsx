'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';

export default function AnalyticsPage() {
  const [trends, setTrends] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any>('/dashboard/trends');
        setTrends(res);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Analytics & Performance</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-xs">
          <h2 className="font-bold text-slate-800 mb-3">Risk Distribution</h2>
          <div className="space-y-2">
            {(trends?.risk_score_distribution || []).map((b: any, idx: number) => (
              <div key={idx} className="flex justify-between border-b border-slate-100 pb-1">
                <span>{b.band}</span>
                <span className="font-bold">{b.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
