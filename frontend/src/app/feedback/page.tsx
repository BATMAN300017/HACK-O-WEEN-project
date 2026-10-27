'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';

export default function FeedbackLearningPage() {
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any>('/learning/status');
        setStatus(res);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Feedback & Controlled Continuous Learning</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-xs">
          <div className="text-slate-500 font-semibold uppercase">Active Model</div>
          <div className="text-lg font-bold text-slate-900 mt-1">{status?.current_active_model || 'Loading...'}</div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-xs">
          <div className="text-slate-500 font-semibold uppercase">Training Data Readiness</div>
          <div className="text-lg font-bold text-purple-600 mt-1">{status?.training_data_readiness || 'Loading...'}</div>
          <div className="text-slate-400 mt-0.5">{status?.labeled_samples_count} / 20 samples</div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm text-xs">
          <div className="text-slate-500 font-semibold uppercase">Candidate Status</div>
          <div className="text-lg font-bold text-slate-700 mt-1">{status?.candidate_model_available ? 'Ready' : 'None'}</div>
        </div>
      </div>
    </div>
  );
}
