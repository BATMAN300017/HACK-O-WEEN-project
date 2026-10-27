'use client';

import React, { useEffect, useState } from 'react';

export default function HomePage() {
  const [kpis, setKpis] = useState({
    transactions: 1002,
    alerts: 32,
    investigations: 8,
    confirmedFraud: 3,
    fpr: 25.0,
  });

  const [activeTab, setActiveTab] = useState<'overview' | 'alerts' | 'investigations'>('overview');
  const [scenarioStatus, setScenarioStatus] = useState<string | null>(null);

  const sampleAlerts = [
    { ref: 'ALT-2026-101', acc: 'ACT-2001', score: 88.5, sev: 'CRITICAL', title: 'Rapid Inbound to Outbound Wire Forwarding' },
    { ref: 'ALT-2026-102', acc: 'ACT-2014', score: 76.2, sev: 'HIGH', title: 'Shared Hardware Fingerprint Across 4 Accounts' },
    { ref: 'ALT-2026-103', acc: 'ACT-2035', score: 62.0, sev: 'ELEVATED', title: 'MAD Statistical Amount Deviation on Dormant Account' },
    { ref: 'ALT-2026-104', acc: 'ACT-2089', score: 38.4, sev: 'LOW', title: 'First-time Destination Beneficiary Transfer' },
  ];

  async function triggerScenario(name: string) {
    setScenarioStatus(`Injecting scenario '${name}' into detection engine...`);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/simulation/scenario/${name}`, { method: 'POST' });
      const data = await res.json();
      setScenarioStatus(`Scenario '${name}' injected ${data.events_created || 2} deterministic events.`);
    } catch {
      setScenarioStatus(`Executed scenario: ${name} (offline demo mode)`);
    }
    setTimeout(() => setScenarioStatus(null), 4000);
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 font-sans">
      {/* Header */}
      <header className="bg-slate-900 text-white border-b border-slate-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center font-bold text-slate-900 text-base">SF</div>
          <div>
            <span className="font-bold text-lg tracking-tight">SentinelFlow <span className="text-sky-400">AI</span></span>
            <span className="ml-3 bg-slate-800 text-sky-300 text-xs px-2.5 py-0.5 rounded-full border border-sky-500/30">Fraud Command Center</span>
          </div>
        </div>

        {/* Quick Scenario Triggers */}
        <div className="flex items-center space-x-2 bg-slate-800 p-1.5 rounded-lg border border-slate-700 text-xs">
          <span className="text-slate-400 px-1 font-medium">Inject Scenario:</span>
          <button onClick={() => triggerScenario('rapid_movement')} className="bg-sky-600 hover:bg-sky-500 text-white px-2.5 py-1 rounded font-medium transition">Rapid Flow</button>
          <button onClick={() => triggerScenario('connected_network')} className="bg-amber-600 hover:bg-amber-500 text-white px-2.5 py-1 rounded font-medium transition">Mule Network</button>
          <button onClick={() => triggerScenario('legitimate_unusual')} className="bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded font-medium transition">Benign Burst</button>
        </div>
      </header>

      {/* Notification Toast */}
      {scenarioStatus && (
        <div className="bg-sky-500 text-white text-xs px-4 py-2 text-center font-medium shadow-md transition">
          {scenarioStatus}
        </div>
      )}

      {/* Main Container */}
      <main className="max-w-7xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Financial Crime Surveillance Dashboard</h1>
          <p className="text-xs text-slate-500 mt-1">Multi-modal hybrid risk scoring, graph topological signals, and controlled continuous learning.</p>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Processed Transactions</div>
            <div className="text-2xl font-bold text-slate-900 mt-2">{kpis.transactions.toLocaleString()}</div>
            <div className="text-xs text-emerald-600 font-medium mt-1">42.5 TPM Steady Rate</div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Alerts Generated</div>
            <div className="text-2xl font-bold text-amber-600 mt-2">{kpis.alerts}</div>
            <div className="text-xs text-slate-500 mt-1">Multi-signal detections</div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Investigations</div>
            <div className="text-2xl font-bold text-sky-600 mt-2">{kpis.investigations}</div>
            <div className="text-xs text-slate-500 mt-1">6 High Priority Dossiers</div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Confirmed Fraud / FPR</div>
            <div className="text-2xl font-bold text-red-600 mt-2">{kpis.confirmedFraud} Cases</div>
            <div className="text-xs text-slate-500 mt-1">Verified FPR: {kpis.fpr}%</div>
          </div>
        </div>

        {/* Risk Calibration Tiers */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Normalized 0–100 Risk Ensemble Tiers</h2>
          <div className="grid grid-cols-4 gap-3 text-center text-xs">
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="font-bold text-emerald-800">Routine (0–24)</div>
              <div className="text-lg font-bold text-emerald-700 mt-1">942</div>
              <div className="text-slate-500 text-[11px]">Automated Clear</div>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="font-bold text-blue-800">Low (25–49)</div>
              <div className="text-lg font-bold text-blue-700 mt-1">28</div>
              <div className="text-slate-500 text-[11px]">Audit Sample</div>
            </div>
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="font-bold text-amber-800">Elevated (50–74)</div>
              <div className="text-lg font-bold text-amber-700 mt-1">20</div>
              <div className="text-slate-500 text-[11px]">Analyst Triage</div>
            </div>
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="font-bold text-red-800">High (75–100)</div>
              <div className="text-lg font-bold text-red-700 mt-1">12</div>
              <div className="text-slate-500 text-[11px]">Self-Directed Dossier</div>
            </div>
          </div>
        </div>

        {/* Priority Alerts Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Priority Alert Review Queue</h2>
            <span className="text-xs text-slate-500">Hybrid Ensemble: 30% Rules | 25% MAD Anomaly | 25% ML | 20% Graph</span>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Alert Ref</th>
                <th className="px-5 py-3">Account</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Risk Score</th>
                <th className="px-5 py-3">Finding Title</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sampleAlerts.map(a => (
                <tr key={a.ref} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-mono font-bold text-sky-700">{a.ref}</td>
                  <td className="px-5 py-3 font-mono text-slate-600">{a.acc}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      a.sev === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                      a.sev === 'HIGH' ? 'bg-amber-100 text-amber-800' :
                      a.sev === 'ELEVATED' ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'
                    }`}>{a.sev}</span>
                  </td>
                  <td className="px-5 py-3 font-mono font-bold text-slate-900">{a.score.toFixed(1)}/100</td>
                  <td className="px-5 py-3 font-medium text-slate-800">{a.title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
