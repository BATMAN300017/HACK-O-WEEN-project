'use client';

import React from 'react';

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Platform Settings</h1>
      <div className="bg-white p-6 rounded-xl border border-slate-200 text-xs space-y-3 shadow-sm">
        <h2 className="font-semibold text-slate-800">Operational Configuration</h2>
        <div>Environment: <b>Development / Local Simulation</b></div>
        <div>Active Model: <b>Calibrated Logistic Regression v1.0</b></div>
        <div>Ensemble Weights: <b>30% Rules, 25% MAD Anomaly, 25% ML, 20% Graph</b></div>
      </div>
    </div>
  );
}
