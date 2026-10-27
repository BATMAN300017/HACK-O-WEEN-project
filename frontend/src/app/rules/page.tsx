'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';

export default function RulesPage() {
  const [rules, setRules] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any[]>('/rules');
        setRules(res || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Configurable Detection Rules</h1>
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm text-xs">
        <table className="w-full text-left">
          <thead className="bg-slate-50 font-semibold border-b border-slate-200">
            <tr>
              <th className="px-5 py-3">Code</th>
              <th className="px-5 py-3">Name</th>
              <th className="px-5 py-3">Severity</th>
              <th className="px-5 py-3">Thresholds</th>
              <th className="px-5 py-3">Version</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rules.map(r => (
              <tr key={r.id}>
                <td className="px-5 py-3 font-mono font-bold text-sky-700">{r.rule_code}</td>
                <td className="px-5 py-3">{r.name}</td>
                <td className="px-5 py-3">{r.severity}</td>
                <td className="px-5 py-3 font-mono">{JSON.stringify(r.thresholds)}</td>
                <td className="px-5 py-3 font-mono">v{r.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
