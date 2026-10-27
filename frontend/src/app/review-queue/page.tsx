'use client';

import React from 'react';
import Link from 'next/link';

export default function ReviewQueuePage() {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Analyst Review Queue</h1>
      <p className="text-slate-500 text-sm">Prioritized queue of alerts and investigations requiring peer review or triage.</p>
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-xs space-y-3">
        <p>Review items requiring senior approval or disposition sign-off.</p>
        <Link href="/alerts" className="text-sky-600 font-semibold block">Navigate to Priority Alerts Queue &rarr;</Link>
      </div>
    </div>
  );
}
