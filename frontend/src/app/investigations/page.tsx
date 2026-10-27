'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';

export default function InvestigationsPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadCases() {
      try {
        const res = await fetchApi<any>('/investigations?page_size=50');
        setCases(res.items || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadCases();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Investigations Workspace</h1>
          <p className="text-slate-500 text-sm">Formal evidentiary cases, peer reviews, and final dispositions.</p>
        </div>
        <Link href="/dashboard" className="text-xs font-semibold text-sky-600">&larr; Back to Dashboard</Link>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="px-5 py-3">Case Number</th>
              <th className="px-5 py-3">Title</th>
              <th className="px-5 py-3">Priority</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Completeness</th>
              <th className="px-5 py-3">Disposition</th>
              <th className="px-5 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={7} className="text-center py-6 text-slate-400">Loading cases...</td></tr>
            ) : cases.map(c => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="px-5 py-3 font-mono font-bold text-sky-700">{c.case_number}</td>
                <td className="px-5 py-3 font-medium text-slate-900">{c.title}</td>
                <td className="px-5 py-3 font-semibold">{c.priority}</td>
                <td className="px-5 py-3 font-medium text-slate-700">{c.status}</td>
                <td className="px-5 py-3 font-mono text-sky-600 font-semibold">{c.evidence_completeness_score}%</td>
                <td className="px-5 py-3 font-semibold">{c.disposition || 'In Progress'}</td>
                <td className="px-5 py-3">
                  <Link href={`/investigations/${c.id}`} className="text-sky-600 hover:text-sky-800 font-medium">Open Case &rarr;</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
