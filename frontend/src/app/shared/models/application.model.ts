/**
 * OpenScore Finance — TypeScript Shared Models
 * Clean interfaces matching backend Pydantic schemas and frontend state.
 */

// ── Auth ──────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserRegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  role?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: 'client' | 'agent' | 'admin';
  full_name: string;
  user_id: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'client' | 'agent' | 'admin';
  phone?: string;
  is_active?: boolean;
}

// ── Super Admin ──────────────────────────────────────────────────────
export interface AdminStats {
  total_users: number;
  clients_count: number;
  agents_count: number;
  admins_count: number;
  total_applications: number;
  total_volume_requested: number;
  total_volume_approved: number;
  approval_rate: number;
  portfolio_at_risk_index: number;
  system_average_score: number;
  active_branches: number;
  sector_exposure: Record<string, number>;
  status_summary: Record<string, number>;
}

export interface AdminPrudentialSettings {
  debt_ratio_ceiling: number;
  min_disposable_income: number;
  approval_score_threshold: number;
  counter_proposal_threshold: number;
  rejection_threshold: number;
  bceao_max_monthly_interest: number;
  shap_debt_weight: number;
  shap_income_weight: number;
  shap_regularity_weight: number;
  shap_seniority_weight: number;
  shap_leverage_weight: number;
}

export interface AdminUserCreate {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  role: 'client' | 'agent' | 'admin';
}

export interface AdminResetPasswordPayload {
  new_password: string;
}

export interface AdminClientSummary {
  id: number;
  full_name: string;
  email: string;
  phone?: string;
  is_active: boolean;
  created_at: string;
  activity_sector?: ActivitySector;
  applications_count: number;
  total_requested: number;
  total_approved: number;
  average_score?: number;
  kyc_status: 'complet' | 'partiel' | 'non_verifie';
  monthly_revenue?: number;
  monthly_expenses?: number;
  last_application_status?: string;
  last_application_date?: string;
}

export interface AdminClientDetail {
  id: number;
  full_name: string;
  email: string;
  phone?: string;
  is_active: boolean;
  created_at: string;
  activity_sector?: ActivitySector;
  monthly_revenue?: number;
  monthly_expenses?: number;
  existing_debt?: number;
  business_description?: string;
  years_in_business?: number;
  kyc_status: 'complet' | 'partiel' | 'non_verifie';
  kyc_documents: Record<string, any>;
  applications: Array<{
    id: number;
    reference: string;
    activity_sector: string;
    requested_amount: number;
    requested_duration_months: number;
    status: string;
    agent_name?: string;
    score?: number;
    risk_level?: string;
    approved_amount?: number;
    created_at?: string;
  }>;
  audit_logs: Array<{
    id: number;
    action: string;
    details?: any;
    timestamp?: string;
  }>;
}

export interface AdminClientUpdate {
  full_name?: string;
  phone?: string;
  email?: string;
  is_active?: boolean;
}

export interface AdminAgentSummary {
  id: number;
  full_name: string;
  email: string;
  phone?: string;
  is_active: boolean;
  created_at: string;
  branch: string;
  assigned_applications_count: number;
  certified_applications_count: number;
  pending_applications_count: number;
  approved_volume: number;
  approval_rate: number;
  average_processing_hours: number;
}

export interface AdminAgentReassignPayload {
  target_agent_id: number;
  application_ids?: number[];
}

export interface AdminBranchInfo {
  id: string;
  name: string;
  city: string;
  branch_type: string;
  status: string;
  lead_agent: string;
  agents_count: number;
  active_loans_count: number;
  total_disbursed: number;
  par_30: number;
  max_credit_limit: number;
}

export interface AdminBranchCreate {
  name: string;
  city: string;
  branch_type?: string;
  lead_agent: string;
  max_credit_limit?: number;
}

export interface RiskMatrixData {
  par_30: number;
  par_60: number;
  par_90: number;
  npl_ratio: number;
  guarantee_coverage_rate: number;
  sector_risk: Record<string, {
    exposure_pct: number;
    par_30: number;
    default_rate: number;
    risk_grade: string;
  }>;
  branch_risk: Record<string, {
    active_loans: number;
    exposure: number;
    par_30: number;
  }>;
  stress_test_defaults: {
    income_shock_pct: number;
    inflation_shock_pct: number;
    baseline_par_30: number;
    capital_adequacy_ratio: number;
  };
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
  applicant_phone?: string;
  applicant_email?: string;
  activity_sector: ActivitySector;
  requested_amount: number;
  requested_duration_months: number;
  business_description?: string;
  status: ApplicationStatus;
  agent_id?: number;
  created_at: string;
  updated_at: string;
  is_offline_draft?: boolean;
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

export interface DraftApplication {
  id?: string;
  activity_sector: ActivitySector;
  requested_amount: number;
  requested_duration_months: number;
  business_description?: string;
  created_at: string;
  status: 'offline_pending';
  sync_attempts?: number;
}

export interface ContactClientRequest {
  channel: 'phone' | 'whatsapp' | 'email' | 'in_app';
  subject: string;
  message: string;
}

export interface ApproveDecisionRequest {
  approved_amount?: number;
  notes?: string;
}

export interface RejectApplicationRequest {
  reason: string;
  notes?: string;
}

export interface FieldSurveyRequest {
  guarantee_type?: string;
  guarantee_value?: number;
  market_reputation?: string;
  field_agent_notes?: string;
  daily_cash_flow_observed?: number;
}

export interface PortfolioStats {
  total_applications: number;
  pending_verification: number;
  approved_count: number;
  adjusted_count: number;
  rejected_count: number;
  draft_count: number;
  total_volume_requested: number;
  total_volume_approved: number;
  approval_rate: number;
  average_score: number;
  sector_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
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
  verification_notes?: string;
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

// ── Scoring & Explainability ──────────────────────────────────────────
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
  scored_at?: string;
}

export interface CounterProposalRequest {
  proposed_amount: number;
  proposed_duration_months: number;
}

export interface ApplyCounterProposalRequest {
  proposed_amount: number;
  proposed_duration_months: number;
  notes?: string;
}

// ── Audit Log ─────────────────────────────────────────────────────────
export interface AuditLog {
  id: number;
  application_id: number;
  user_id?: number;
  user_name?: string;
  action: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
}

// ── Receipt ──────────────────────────────────────────────────────────
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

// ── Voice Assist ─────────────────────────────────────────────────────
export interface VoiceQueryResponse {
  response_text: string;
  suggestions: string[];
  detected_intent?: string;
  suggested_field?: { field: string; value: any };
}
