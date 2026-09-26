import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';
import { OfflineSyncService } from './offline-sync.service';
import { ToastService } from './toast.service';
import {
  CreditApplication, ApplicationListResponse, ApplicationCreateRequest,
  ExtractedData, VerifyDataRequest, ScoringResult,
  CounterProposalRequest, ApplyCounterProposalRequest,
  ReceiptData, VoiceQueryResponse, AuditLogListResponse,
  UserRegisterRequest, TokenResponse, PortfolioStats,
  RejectApplicationRequest, FieldSurveyRequest, ContactClientRequest, ApproveDecisionRequest,
  AdminStats, AdminPrudentialSettings, AdminUserCreate, User,
  AdminClientSummary, AdminClientDetail, AdminClientUpdate,
  AdminAgentSummary, AdminAgentReassignPayload, AdminResetPasswordPayload,
  AdminBranchInfo, AdminBranchCreate, RiskMatrixData
} from '../../shared/models/application.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly BASE_URL = environment.apiUrl;

  constructor(
    private auth: AuthService,
    private offlineSync: OfflineSyncService,
    private toast: ToastService,
  ) {}

  /** Generic fetch with JWT auth header */
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.auth.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Only set Content-Type for non-FormData bodies
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(`${this.BASE_URL}${path}`, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        this.auth.logout();
        throw new Error('Session expirée');
      }

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status} - ${response.statusText}`;
        try {
          const errData = await response.json();
          errorMessage = errData.detail || errData.message || errorMessage;
        } catch {
          // Keep default message if not JSON
        }
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error: any) {
      if (!navigator.onLine || error.message?.includes('Failed to fetch') || error.message?.includes('NetworkError')) {
        throw new Error('Connexion réseau indisponible');
      }
      throw error;
    }
  }

  // ── Auth ──────────────────────────────────────────────────────────
  async login(credentials: { email: string; password: string }): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async register(data: UserRegisterRequest): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // ── Portfolio stats (Agent Cockpit) ──────────────────────────────
  async getPortfolioStats(): Promise<PortfolioStats> {
    return this.request<PortfolioStats>('/applications/stats/portfolio');
  }

  // ── Super Admin Endpoints ─────────────────────────────────────────
  async getAdminStats(): Promise<AdminStats> {
    return this.request<AdminStats>('/admin/stats');
  }

  async getAdminUsers(roleFilter?: string, search?: string): Promise<User[]> {
    const params = new URLSearchParams();
    if (roleFilter && roleFilter !== 'all') params.append('role_filter', roleFilter);
    if (search) params.append('search', search);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<User[]>(`/admin/users${query}`);
  }

  async createAdminUser(data: AdminUserCreate): Promise<User> {
    return this.request<User>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async toggleUserActive(userId: number): Promise<{ status: string; user_id: number; is_active: boolean }> {
    return this.request<{ status: string; user_id: number; is_active: boolean }>(`/admin/users/${userId}/toggle-active`, {
      method: 'PATCH',
    });
  }

  async deleteAdminUser(userId: number): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/admin/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async updateUserRole(userId: number, role: string): Promise<User> {
    return this.request<User>(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  }

  async getAdminClients(sector?: string, kycStatus?: string, search?: string): Promise<AdminClientSummary[]> {
    const params = new URLSearchParams();
    if (sector && sector !== 'all') params.append('sector', sector);
    if (kycStatus && kycStatus !== 'all') params.append('kyc_status', kycStatus);
    if (search) params.append('search', search);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<AdminClientSummary[]>(`/admin/clients${query}`);
  }

  async getAdminClientDetail(clientId: number): Promise<AdminClientDetail> {
    return this.request<AdminClientDetail>(`/admin/clients/${clientId}`);
  }

  async updateAdminClient(clientId: number, data: AdminClientUpdate): Promise<User> {
    return this.request<User>(`/admin/clients/${clientId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async getAdminAgents(branch?: string, search?: string): Promise<AdminAgentSummary[]> {
    const params = new URLSearchParams();
    if (branch && branch !== 'all') params.append('branch', branch);
    if (search) params.append('search', search);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<AdminAgentSummary[]>(`/admin/agents${query}`);
  }

  async reassignAgentApplications(agentId: number, data: AdminAgentReassignPayload): Promise<{ status: string; reassigned_count: number; target_agent: string; message: string }> {
    return this.request<{ status: string; reassigned_count: number; target_agent: string; message: string }>(`/admin/agents/${agentId}/reassign`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async resetUserPassword(userId: number, data: AdminResetPasswordPayload): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAdminBranches(): Promise<AdminBranchInfo[]> {
    return this.request<AdminBranchInfo[]>('/admin/branches');
  }

  async createAdminBranch(data: AdminBranchCreate): Promise<AdminBranchInfo> {
    return this.request<AdminBranchInfo>('/admin/branches', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getRiskMatrix(): Promise<RiskMatrixData> {
    return this.request<RiskMatrixData>('/admin/risk-matrix');
  }

  async getPrudentialSettings(): Promise<AdminPrudentialSettings> {
    return this.request<AdminPrudentialSettings>('/admin/settings');
  }

  async updatePrudentialSettings(data: AdminPrudentialSettings): Promise<AdminPrudentialSettings> {
    return this.request<AdminPrudentialSettings>('/admin/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getGlobalAuditLogs(limit: number = 100): Promise<AuditLogListResponse> {
    return this.request<AuditLogListResponse>(`/admin/audit-logs?limit=${limit}`);
  }

  // ── Applications ─────────────────────────────────────────────────
  async getApplications(statusFilter?: string, sectorFilter?: string, branchFilter?: string): Promise<ApplicationListResponse> {
    try {
      let query = '';
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'all') params.append('status_filter', statusFilter);
      if (sectorFilter && sectorFilter !== 'all') params.append('sector_filter', sectorFilter);
      if (branchFilter && branchFilter !== 'all') params.append('branch_filter', branchFilter);
      if (params.toString()) query = `?${params.toString()}`;

      return await this.request<ApplicationListResponse>(`/applications${query}`);
    } catch (err) {
      // Fallback: load offline drafts if offline
      const drafts = await this.offlineSync.getDrafts();
      const mappedDrafts: CreditApplication[] = drafts.map((d, index) => ({
        id: -1 * (index + 1),
        reference: `LOCAL-${d.id?.substring(0, 8) || 'DRAFT'}`,
        applicant_id: 0,
        applicant_name: 'Brouillon Hors-Ligne',
        activity_sector: d.activity_sector,
        requested_amount: d.requested_amount,
        requested_duration_months: d.requested_duration_months,
        business_description: d.business_description,
        status: 'draft',
        created_at: d.created_at,
        updated_at: d.created_at,
        is_offline_draft: true,
      }));
      return { applications: mappedDrafts, total: mappedDrafts.length };
    }
  }

  async getApplication(id: number): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/applications/${id}`);
  }

  async createApplication(data: ApplicationCreateRequest): Promise<CreditApplication> {
    // If offline, save directly to IndexedDB
    if (!navigator.onLine) {
      await this.offlineSync.saveDraft(data);
      return {
        id: 0,
        reference: `OSF-LOCAL-${Date.now().toString().slice(-4)}`,
        applicant_id: 0,
        activity_sector: data.activity_sector,
        requested_amount: data.requested_amount,
        requested_duration_months: data.requested_duration_months,
        business_description: data.business_description,
        status: 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_offline_draft: true,
      };
    }

    try {
      return await this.request<CreditApplication>('/applications', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (e) {
      // Fallback on network failure
      await this.offlineSync.saveDraft(data);
      return {
        id: 0,
        reference: `OSF-OFFLINE-${Date.now().toString().slice(-4)}`,
        applicant_id: 0,
        activity_sector: data.activity_sector,
        requested_amount: data.requested_amount,
        requested_duration_months: data.requested_duration_months,
        business_description: data.business_description,
        status: 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_offline_draft: true,
      };
    }
  }

  // ── Document extraction ──────────────────────────────────────────
  async extractDocuments(appId: number, file: File): Promise<ExtractedData> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request<ExtractedData>(`/applications/${appId}/extract-docs`, {
      method: 'POST',
      body: formData,
    });
  }

  // ── Extracted data ───────────────────────────────────────────────
  async getExtractedData(appId: number): Promise<ExtractedData> {
    return this.request<ExtractedData>(`/applications/${appId}/extracted-data`);
  }

  // ── Verification ─────────────────────────────────────────────────
  async verifyData(appId: number, data: VerifyDataRequest): Promise<ExtractedData> {
    return this.request<ExtractedData>(`/applications/${appId}/verify-data`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ── Field survey & guarantees ────────────────────────────────────
  async updateFieldSurvey(appId: number, data: FieldSurveyRequest): Promise<ExtractedData> {
    return this.request<ExtractedData>(`/applications/${appId}/field-survey`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ── Reject application ───────────────────────────────────────────
  async rejectApplication(appId: number, data: RejectApplicationRequest): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/applications/${appId}/reject`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Audit logs ───────────────────────────────────────────────────
  async getAuditLogs(appId: number): Promise<AuditLogListResponse> {
    return this.request<AuditLogListResponse>(`/applications/${appId}/audit-logs`);
  }

  // ── Scoring ──────────────────────────────────────────────────────
  async evaluateApplication(appId: number): Promise<ScoringResult> {
    return this.request<ScoringResult>(`/applications/${appId}/evaluate`, {
      method: 'POST',
    });
  }

  async getScoringResult(appId: number): Promise<ScoringResult> {
    return this.request<ScoringResult>(`/applications/${appId}/scoring`);
  }

  async recalculateScore(appId: number, proposal: CounterProposalRequest): Promise<ScoringResult> {
    return this.request<ScoringResult>(`/applications/${appId}/recalculate`, {
      method: 'POST',
      body: JSON.stringify(proposal),
    });
  }

  async applyCounterProposal(appId: number, data: ApplyCounterProposalRequest): Promise<ScoringResult> {
    return this.request<ScoringResult>(`/applications/${appId}/apply-counter-proposal`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async approveCreditDecision(appId: number, data?: ApproveDecisionRequest): Promise<ScoringResult> {
    return this.request<ScoringResult>(`/applications/${appId}/approve-decision`, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async contactClient(appId: number, data: ContactClientRequest): Promise<{ status: string; message: string; channel: string; timestamp: string }> {
    return this.request<{ status: string; message: string; channel: string; timestamp: string }>(`/applications/${appId}/contact-client`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Receipt ──────────────────────────────────────────────────────
  async getReceipt(appId: number): Promise<ReceiptData> {
    return this.request<ReceiptData>(`/applications/${appId}/receipt`);
  }

  // ── Microfinance Account & Quick Init ────────────────────────────
  async lookupAccount(accountNumber: string): Promise<any> {
    return this.request<any>(`/applications/accounts/${encodeURIComponent(accountNumber)}`);
  }

  async linkAccount(accountNumber: string): Promise<{ status: string; account_number: string; message: string }> {
    return this.request<{ status: string; account_number: string; message: string }>('/applications/accounts/link', {
      method: 'POST',
      body: JSON.stringify({ account_number: accountNumber }),
    });
  }

  async quickInitApplication(data: {
    account_number: string;
    requested_amount: number;
    requested_duration_months: number;
    business_description?: string;
    branch_code?: string;
    application_type?: string;
    form_data?: any;
    force_override_cross_branch?: boolean;
  }): Promise<CreditApplication> {
    return this.request<CreditApplication>('/applications/quick-init', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateApplicationFormData(appId: number, formData: any): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/applications/${appId}/form-data`, {
      method: 'PATCH',
      body: JSON.stringify({ form_data: formData }),
    });
  }

  async searchApplications(search: string): Promise<ApplicationListResponse> {
    return this.request<ApplicationListResponse>(`/applications/search?q=${encodeURIComponent(search)}`);
  }

  // ── Multi-Guarantees ─────────────────────────────────────────────
  async getGuarantees(appId: number): Promise<any[]> {
    return this.request<any[]>(`/applications/${appId}/guarantees`);
  }

  async addGuarantee(appId: number, data: any): Promise<any> {
    return this.request<any>(`/applications/${appId}/guarantees`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteGuarantee(appId: number, guaranteeId: number): Promise<any> {
    return this.request<any>(`/applications/${appId}/guarantees/${guaranteeId}`, {
      method: 'DELETE',
    });
  }

  // ── Multi-Debts ──────────────────────────────────────────────────
  async getDebts(appId: number): Promise<any[]> {
    return this.request<any[]>(`/applications/${appId}/debts`);
  }

  async addDebt(appId: number, data: any): Promise<any> {
    return this.request<any>(`/applications/${appId}/debts`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteDebt(appId: number, debtId: number): Promise<any> {
    return this.request<any>(`/applications/${appId}/debts/${debtId}`, {
      method: 'DELETE',
    });
  }

  // ── Committee Workflow ───────────────────────────────────────────
  async submitToCommittee(appId: number): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/applications/${appId}/submit-to-committee`, {
      method: 'POST',
    });
  }

  async getPendingCommitteeApprovals(): Promise<any[]> {
    const res = await this.request<any>('/admin/pending-approvals');
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.applications)) return res.applications;
    return [];
  }

  async processCommitteeDecision(
    appId: number,
    data: { decision: string; approved_amount?: number; approved_duration_months?: number; notes?: string }
  ): Promise<any> {
    return this.request<any>(`/admin/applications/${appId}/committee-decision`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async requestCommitteeDocument(appId: number, data: { document_name: string; description?: string }): Promise<any> {
    return this.request<any>(`/admin/applications/${appId}/request-document`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async uploadRequestedDocument(appId: number, file: File, requestId?: string, notes?: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (requestId) formData.append('request_id', requestId);
    if (notes) formData.append('notes', notes);

    return this.request<any>(`/applications/${appId}/upload-requested-document`, {
      method: 'POST',
      body: formData,
    });
  }

  // ── Dynamic Scoring Policy & Granting Methods (Admin) ─────────────
  async getAdminScoringPolicy(): Promise<any> {
    return this.request<any>('/admin/scoring/policy');
  }

  async createAdminScoringPolicy(data: any): Promise<any> {
    return this.request<any>('/admin/scoring/policy', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async addScoringVariable(data: any): Promise<any> {
    return this.request<any>('/admin/scoring/variables', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateScoringVariable(varId: number, data: any): Promise<any> {
    return this.request<any>(`/admin/scoring/variables/${varId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteScoringVariable(varId: number): Promise<any> {
    return this.request<any>(`/admin/scoring/variables/${varId}`, {
      method: 'DELETE',
    });
  }

  async getGrantingMethods(): Promise<any[]> {
    return this.request<any[]>('/admin/granting-methods');
  }

  async createGrantingMethod(data: any): Promise<any> {
    return this.request<any>('/admin/granting-methods', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateGrantingMethod(id: number, data: any): Promise<any> {
    return this.request<any>(`/admin/granting-methods/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ── Agent Evaluations ────────────────────────────────────────────
  async getAgentEvaluations(agentId: number): Promise<any[]> {
    return this.request<any[]>(`/admin/agents/${agentId}/evaluations`);
  }

  async evaluateAgent(agentId: number, data: { rating: number; criteria_scores?: any; comments?: string }): Promise<any> {
    return this.request<any>(`/admin/agents/${agentId}/evaluations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAllEvaluations(): Promise<any[]> {
    return this.request<any[]>('/admin/evaluations');
  }

  // ── Committee Reports ────────────────────────────────────────────
  async getCommitteeReports(): Promise<any[]> {
    return this.request<any[]>('/admin/committee/reports');
  }

  async createCommitteeReport(data: { title: string; meeting_date: string; file_name: string; file_url: string; file_size?: number; notes?: string }): Promise<any> {
    return this.request<any>('/admin/committee/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Kafo Jiginew Account Requests ────────────────────────────────
  async requestKafoJiginewAccount(data: any): Promise<any> {
    return this.request<any>('/accounts/kafo-jiginew-request', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listKafoJiginewRequests(branchCode: string = 'all', statusFilter: string = 'all'): Promise<any[]> {
    return this.request<any[]>(`/accounts/kafo-jiginew-requests?branch_code=${branchCode}&status_filter=${statusFilter}`);
  }

  async approveKafoJiginewRequest(requestId: number): Promise<any> {
    return this.request<any>(`/accounts/kafo-jiginew-requests/${requestId}/approve`, {
      method: 'POST',
    });
  }

  // ── Voice Assist ─────────────────────────────────────────────────
  async voiceQuery(queryText: string, language: string = 'fr'): Promise<VoiceQueryResponse> {
    return this.request<VoiceQueryResponse>('/assist/voice-query', {
      method: 'POST',
      body: JSON.stringify({ query_text: queryText, language }),
    });
  }
}

