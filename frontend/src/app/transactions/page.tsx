'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import { formatCurrency, formatDate } from '@/lib/formatters';
import Link from 'next/link';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any>('/transactions?page_size=50');
        setTransactions(res.items || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Transactions Ledger</h1>
          <p className="text-slate-500 text-sm">Real-time financial transaction events and risk classifications.</p>
        </div>
        <Link href="/dashboard" className="text-xs font-semibold text-sky-600">&larr; Back to Dashboard</Link>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="px-5 py-3">Transaction ID</th>
              <th className="px-5 py-3">Amount</th>
              <th className="px-5 py-3">Source Account</th>
              <th className="px-5 py-3">Beneficiary</th>
              <th className="px-5 py-3">Channel</th>
              <th className="px-5 py-3">Risk Score</th>
              <th className="px-5 py-3">Risk Band</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={7} className="text-center py-6 text-slate-400">Loading transactions...</td></tr>
            ) : transactions.map(t => (
              <tr key={t.id} className="hover:bg-slate-50">
                <td className="px-5 py-3 font-mono font-medium text-slate-700">{t.id}</td>
                <td className="px-5 py-3 font-semibold text-slate-900">{formatCurrency(t.amount, t.currency)}</td>
                <td className="px-5 py-3 font-mono text-slate-600">{t.source_account_id}</td>
                <td className="px-5 py-3 text-slate-700">{t.beneficiary_name || t.destination_account_id || 'N/A'}</td>
                <td className="px-5 py-3 text-slate-500">{t.payment_channel}</td>
                <td className="px-5 py-3 font-mono font-bold">{t.risk_score?.toFixed(1)}</td>
                <td className="px-5 py-3 font-semibold">{t.risk_band}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
