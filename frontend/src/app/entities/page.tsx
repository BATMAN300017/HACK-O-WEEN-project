'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import Link from 'next/link';

export default function EntitiesPage() {
  const [entities, setEntities] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetchApi<any[]>('/entities');
        setEntities(res || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Entity Explorer</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {entities.map(e => (
          <div key={e.id} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm text-xs space-y-1">
            <div className="font-bold text-slate-900">{e.label}</div>
            <div className="text-slate-500 font-mono">{e.type}: {e.identifier}</div>
            <Link href={`/entities/${e.id}`} className="text-sky-600 font-semibold block pt-2">View Profile &rarr;</Link>
          </div>
        ))}
      </div>
    </div>
  );
}
