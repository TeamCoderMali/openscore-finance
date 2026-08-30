import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import {
  CreditApplication, ApplicationListResponse, ApplicationCreateRequest,
  ExtractedData, VerifyDataRequest, ScoringResult,
  CounterProposalRequest, ReceiptData, VoiceQueryResponse
} from '../../shared/models/application.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly BASE_URL = 'http://localhost:8000/api/v1';

  constructor(private auth: AuthService) {}

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
  }

  // ── Applications ─────────────────────────────────────────────────
  async getApplications(): Promise<ApplicationListResponse> {
    return this.request<ApplicationListResponse>('/applications');
  }

  async getApplication(id: number): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/applications/${id}`);
  }

  async createApplication(data: ApplicationCreateRequest): Promise<CreditApplication> {
    return this.request<CreditApplication>('/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
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

  // ── Receipt ──────────────────────────────────────────────────────
  async getReceipt(appId: number): Promise<ReceiptData> {
    return this.request<ReceiptData>(`/applications/${appId}/receipt`);
  }

  // ── Voice Assist ─────────────────────────────────────────────────
  async voiceQuery(queryText: string): Promise<VoiceQueryResponse> {
    return this.request<VoiceQueryResponse>('/assist/voice-query', {
      method: 'POST',
      body: JSON.stringify({ query_text: queryText, language: 'fr' }),
    });
  }
}
