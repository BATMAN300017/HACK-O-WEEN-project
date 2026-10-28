export interface Transaction {
  id: string;
  event_id: string;
  source_account_id: string;
  destination_account_id?: string;
  beneficiary_name?: string;
  customer_id: string;
  amount: number;
  currency: string;
  transaction_type: string;
  payment_channel: string;
  risk_score: number;
  risk_band: 'ROUTINE' | 'LOW' | 'ELEVATED' | 'HIGH';
  status: string;
  created_at: string;
}

export interface Alert {
  id: string;
  alert_ref: string;
  transaction_id: string;
  account_id: string;
  customer_id: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: string;
  risk_score: number;
  title: string;
  summary: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
}

export interface Investigation {
  id: string;
  case_number: string;
  title: string;
  summary: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: string;
  disposition?: string;
  disposition_rationale?: string;
  evidence_completeness_score: number;
  created_at: string;
  updated_at: string;
}

export interface EvidenceItem {
  id: string;
  investigation_id: string;
  evidence_type: string;
  description: string;
  observed_facts: Record<string, unknown>;
  verification_status: string;
  collector: string;
  integrity_hash?: string;
  created_at: string;
}
