/**
 * OpenScore Finance — TypeScript Models
 * Shared interfaces matching backend Pydantic schemas.
 */

// ── Auth ──────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: 'client' | 'agent';
  full_name: string;
  user_id: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'client' | 'agent';
  phone?: string;
}

// ── Application ──────────────────────────────────────────────────────
export type ActivitySector = 'Commerce' | 'Agriculture' | 'Artisanat' | 'TPE';

export type ApplicationStatus =
  | 'draft'
  | 'documents_uploaded'
  | 'data_extracted'
  | 'pending_verification'
  | 'data_verified'
  | 'scored'
  | 'approved'
  | 'adjusted'
  | 'rejected';

export interface CreditApplication {
  id: number;
  reference: string;
  applicant_id: number;
  applicant_name?: string;
  activity_sector: ActivitySector;
  requested_amount: number;
  requested_duration_months: number;
  business_description?: string;
  status: ApplicationStatus;
  agent_id?: number;
  created_at: string;
  updated_at: string;
}

export interface ApplicationListResponse {
  applications: CreditApplication[];
  total: number;
}

export interface ApplicationCreateRequest {
  activity_sector: ActivitySector;
  requested_amount: number;
  requested_duration_months: number;
  business_description?: string;
}

// ── Extracted Data ──────────────────────────────────────────────────
export interface ExtractedData {
  id: number;
  application_id: number;
  full_name?: string;
  date_of_birth?: string;
  id_number?: string;
  id_type?: string;
  monthly_revenue?: number;
  monthly_expenses?: number;
  existing_debt?: number;
  business_registration_number?: string;
  business_start_date?: string;
  years_in_business?: number;
  revenue_regularity_months?: number;
  is_verified: boolean;
  extraction_confidence?: number;
  raw_extraction_json?: Record<string, unknown>;
}

export interface VerifyDataRequest {
  full_name?: string;
  date_of_birth?: string;
  id_number?: string;
  id_type?: string;
  monthly_revenue?: number;
  monthly_expenses?: number;
  existing_debt?: number;
  business_registration_number?: string;
  business_start_date?: string;
  years_in_business?: number;
  revenue_regularity_months?: number;
  verification_notes?: string;
}

// ── Scoring ─────────────────────────────────────────────────────────
export type RiskLevel = 'low' | 'medium' | 'high' | 'very_high';

export interface ExplainabilityItem {
  variable: string;
  label: string;
  value: string;
  impact: 'positive' | 'negative' | 'neutral';
  weight: number;
  contribution: number;
  detail: string;
}

export interface ScoringResult {
  id: number;
  application_id: number;
  score: number;
  risk_level: RiskLevel;
  decision: 'approved' | 'adjusted' | 'rejected';
  approved_amount?: number;
  proposed_amount?: number;
  proposed_duration_months?: number;
  explainability: ExplainabilityItem[];
  debt_ratio?: number;
  disposable_income?: number;
  scored_at: string;
}

export interface CounterProposalRequest {
  proposed_amount: number;
  proposed_duration_months: number;
}

// ── Receipt ─────────────────────────────────────────────────────────
export interface ReceiptData {
  reference: string;
  applicant_name: string;
  applicant_email: string;
  applicant_phone?: string;
  activity_sector: string;
  requested_amount: number;
  decision: string;
  approved_amount?: number;
  proposed_amount?: number;
  proposed_duration_months?: number;
  score: number;
  risk_level: string;
  agent_name?: string;
  scored_at: string;
  created_at: string;
  receipt_id: string;
}

// ── Voice Assist ────────────────────────────────────────────────────
export interface VoiceQueryResponse {
  response_text: string;
  suggestions: string[];
}
