'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import { formatCurrency } from '@/lib/formatters';
import Link from 'next/link';

export default function DashboardPage() {
  const [kpis, setKpis] = useState<any>(null);
  const [recentAlerts, setRecentAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const summary = await fetchApi<any>('/dashboard/summary');
        setKpis(summary);
        const alerts = await fetchApi<any>('/alerts?page_size=5');
        setRecentAlerts(alerts.items || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Fraud Command Center</h1>
        <p className="text-slate-500 mt-1">Autonomous surveillance, graph correlation, and controlled learning.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading telemetry...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Transactions Processed</div>
              <div className="text-3xl font-bold text-slate-900 mt-2">{kpis?.transactions_processed?.toLocaleString()}</div>
              <div className="text-xs text-emerald-600 font-medium mt-1">42.5 TPM throughput</div>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Alerts Generated</div>
              <div className="text-3xl font-bold text-amber-600 mt-2">{kpis?.alerts_generated?.toLocaleString()}</div>
              <div className="text-xs text-slate-500 mt-1">Requiring investigation</div>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Open Investigations</div>
              <div className="text-3xl font-bold text-sky-600 mt-2">{kpis?.open_investigations?.toLocaleString()}</div>
              <div className="text-xs text-slate-500 mt-1">{kpis?.high_priority_cases} High Priority</div>
            </div>
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Confirmed Fraud / FPR</div>
              <div className="text-3xl font-bold text-red-600 mt-2">{kpis?.confirmed_fraud_count}</div>
              <div className="text-xs text-slate-500 mt-1">FPR: {kpis?.verified_false_positive_rate}%</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-900">Priority Alerts Awaiting Review</h2>
              <Link href="/alerts" className="text-xs font-semibold text-sky-600 hover:text-sky-700">View All Alerts &rarr;</Link>
            </div>
            <div className="divide-y divide-slate-100">
              {recentAlerts.map(alert => (
                <div key={alert.id} className="py-3 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-mono font-bold text-sky-700">{alert.alert_ref}</div>
                    <div className="font-medium text-slate-900 mt-0.5">{alert.title}</div>
                    <div className="text-slate-500 mt-0.5">{alert.summary}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-bold text-slate-800 text-sm">{alert.risk_score.toFixed(1)}/100</span>
                    <div className="text-[10px] text-slate-400 mt-0.5">{alert.severity}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
