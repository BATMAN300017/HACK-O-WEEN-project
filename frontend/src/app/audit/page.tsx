'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';

export default function AuditPage() {
  const [audit, setAudit] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any>('/audit?page_size=50');
        setAudit(res.items || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Immutable Audit Trail</h1>
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm text-xs">
        <table className="w-full text-left">
          <thead className="bg-slate-50 font-semibold border-b border-slate-200">
            <tr>
              <th className="px-5 py-3">Timestamp</th>
              <th className="px-5 py-3">Actor</th>
              <th className="px-5 py-3">Action</th>
              <th className="px-5 py-3">Resource</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {audit.map(a => (
              <tr key={a.id}>
                <td className="px-5 py-3 text-slate-400 font-mono">{a.created_at}</td>
                <td className="px-5 py-3 font-medium">{a.actor_name}</td>
                <td className="px-5 py-3 font-mono text-sky-700 font-bold">{a.action}</td>
                <td className="px-5 py-3 font-mono">{a.resource_type}:{a.resource_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
