'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const res = await fetchApi<any>('/alerts?page_size=50');
        setAlerts(res.items || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadAlerts();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Alerts Queue</h1>
          <p className="text-slate-500 text-sm">Review incoming alerts produced by multi-signal detection engines.</p>
        </div>
        <Link href="/dashboard" className="text-xs font-semibold text-sky-600">&larr; Back to Dashboard</Link>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th class="px-5 py-3">Alert Ref</th>
              <th class="px-5 py-3">Severity</th>
              <th class="px-5 py-3">Risk Score</th>
              <th class="px-5 py-3">Account</th>
              <th class="px-5 py-3">Title</th>
              <th class="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={6} className="text-center py-6 text-slate-400">Loading alerts...</td></tr>
            ) : alerts.map(a => (
              <tr key={a.id} className="hover:bg-slate-50">
                <td className="px-5 py-3 font-mono font-bold text-sky-700">{a.alert_ref}</td>
                <td className="px-5 py-3 font-semibold">{a.severity}</td>
                <td className="px-5 py-3 font-mono font-bold">{a.risk_score.toFixed(1)}</td>
                <td className="px-5 py-3 font-mono text-slate-600">{a.account_id}</td>
                <td className="px-5 py-3 text-slate-800">{a.title}</td>
                <td className="px-5 py-3 text-slate-500">{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
