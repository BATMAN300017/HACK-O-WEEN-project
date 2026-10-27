'use client';

import React from 'react';

export default function IntelligencePage() {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">AI Investigation Copilot</h1>
      <div className="p-6 bg-white rounded-xl border border-slate-200 text-xs text-slate-600 space-y-3 shadow-sm">
        <p className="font-semibold text-slate-800">Evidence-Grounded Natural-Language Intelligence</p>
        <p>SentinelFlow AI Copilot operates directly inside case dossiers to assist investigators by answering questions with strict evidentiary citations.</p>
        <p className="text-slate-400">Open any active investigation from the Investigations workspace to engage with the live Copilot session.</p>
      </div>
    </div>
  );
}
