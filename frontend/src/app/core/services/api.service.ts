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
  RejectApplicationRequest, FieldSurveyRequest,
  AdminStats, AdminPrudentialSettings, AdminUserCreate, User
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
        const error = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        throw new Error(error.detail || `Erreur ${response.status}`);
      }

      return response.json();
    } catch (err: any) {
      if (!navigator.onLine || err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
        throw new Error('Connexion réseau indisponible');
      }
      throw err;
    }
  }

  // ── Auth ─────────────────────────────────────────────────────────
  async register(data: UserRegisterRequest): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
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
  async getApplications(statusFilter?: string, sectorFilter?: string): Promise<ApplicationListResponse> {
    try {
      let query = '';
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'all') params.append('status_filter', statusFilter);
      if (sectorFilter && sectorFilter !== 'all') params.append('sector_filter', sectorFilter);
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

  async approveCreditDecision(appId: number): Promise<ScoringResult> {
    return this.request<ScoringResult>(`/applications/${appId}/approve-decision`, {
      method: 'POST',
    });
  }

  // ── Receipt ──────────────────────────────────────────────────────
  async getReceipt(appId: number): Promise<ReceiptData> {
    return this.request<ReceiptData>(`/applications/${appId}/receipt`);
  }

  // ── Voice Assist ─────────────────────────────────────────────────
  async voiceQuery(queryText: string, language: string = 'fr'): Promise<VoiceQueryResponse> {
    return this.request<VoiceQueryResponse>('/assist/voice-query', {
      method: 'POST',
      body: JSON.stringify({ query_text: queryText, language }),
    });
  }
}
