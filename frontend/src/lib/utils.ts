import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const RISK_BANDS = {
  ROUTINE: { label: 'Routine', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  LOW: { label: 'Low', color: 'text-blue-700 bg-blue-50 border-blue-200' },
  ELEVATED: { label: 'Elevated', color: 'text-amber-700 bg-amber-50 border-amber-200' },
  HIGH: { label: 'High Priority', color: 'text-red-700 bg-red-50 border-red-200' },
} as const;
