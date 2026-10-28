'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';
import type { Alert } from '@/types/alert';

interface DashboardSummary {
  transactions_processed: number;
  transactions_per_minute: number;
  alerts_generated: number;
  open_investigations: number;
  high_priority_cases: number;
  verified_false_positive_rate: number;
  confirmed_fraud_count: number;
}

interface AlertListResponse {
  items: Alert[];
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<DashboardSummary | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [summary, alerts] = await Promise.all([
          fetchApi<DashboardSummary>('/dashboard/summary'),
          fetchApi<AlertListResponse>('/alerts?page_size=5'),
        ]);
        setKpis(summary);
        setRecentAlerts(alerts.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load dashboard data.');
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
      ) : error ? (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">
          Unable to load dashboard data: {error}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Transactions Processed</div>
              <div className="text-3xl font-bold text-slate-900 mt-2">{kpis?.transactions_processed?.toLocaleString()}</div>
              <div className="text-xs text-emerald-600 font-medium mt-1">{kpis?.transactions_per_minute.toFixed(1)} TPM throughput</div>
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
