'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api-client';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('sarah_investigator');
  const [password, setPassword] = useState('password123');

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await fetchApi<any>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
      });
      localStorage.setItem('sentinel_token', res.access_token);
      router.push('/dashboard');
    } catch (err: any) {
      alert('Login error: ' + err.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
      <div className="bg-white rounded-xl shadow-xl p-8 max-w-sm w-full space-y-4">
        <h1 className="text-xl font-bold text-slate-900">SentinelFlow AI</h1>
        <p className="text-xs text-slate-500">Sign in to your fraud investigation workspace</p>
        <form onSubmit={handleLogin} className="space-y-3 text-xs">
          <div>
            <label className="block text-slate-700 font-medium mb-1">Username</label>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2" />
          </div>
          <div>
            <label className="block text-slate-700 font-medium mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2" />
          </div>
          <button type="submit" className="w-full bg-sky-600 hover:bg-sky-500 text-white font-medium py-2 rounded-lg transition">Sign In</button>
        </form>
      </div>
    </div>
  );
}
