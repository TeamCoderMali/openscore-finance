import { Injectable, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { User, TokenResponse } from '../../shared/models/application.model';

export interface RegisterPayload {
  fullName: string;
  email: string;
  password: string;
  phone?: string;
  idNumber?: string;
  idType?: string;
  city?: string;
  activitySector?: string;
  monthlyRevenue?: number;
  monthlyExpenses?: number;
  existingDebt?: number;
  yearsInBusiness?: number;
  revenueRegularityMonths?: number;
  requestedAmount?: number;
  businessDescription?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'osf_token';
  private readonly USER_KEY = 'osf_user';
  private readonly BASE_URL = environment.apiUrl;

  currentUser = signal<User | null>(this.loadUser());
  token = signal<string | null>(this.loadToken());

  isAuthenticated = computed(() => !!this.token());
  userRole = computed(() => this.currentUser()?.role || null);
  userName = computed(() => this.currentUser()?.full_name || '');

  constructor(private router: Router) {}

  private loadToken(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private loadUser(): User | null {
    if (typeof localStorage === 'undefined') return null;
    const data = localStorage.getItem(this.USER_KEY);
    return data ? JSON.parse(data) : null;
  }

  getToken(): string | null {
    return this.token();
  }

  async login(email: string, pass: string): Promise<User> {
    const response = await fetch(`${this.BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: pass }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Identifiants invalides' }));
      throw new Error(error.detail || 'Échec de connexion');
    }

    const data: TokenResponse = await response.json();
    return this.setSession(data, email);
  }

  async register(payload: RegisterPayload): Promise<User> {
    const response = await fetch(`${this.BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: payload.fullName,
        email: payload.email,
        password: payload.password,
        phone: payload.phone,
        role: 'client',
        id_number: payload.idNumber,
        id_type: payload.idType || 'NINA',
        city: payload.city,
        activity_sector: payload.activitySector || 'Commerce',
        monthly_revenue: payload.monthlyRevenue,
        monthly_expenses: payload.monthlyExpenses,
        existing_debt: payload.existingDebt || 0,
        years_in_business: payload.yearsInBusiness || 3,
        revenue_regularity_months: payload.revenueRegularityMonths || 12,
        requested_amount: payload.requestedAmount,
        business_description: payload.businessDescription,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Échec de l'inscription" }));
      throw new Error(error.detail || "Échec de l'inscription");
    }

    const data: TokenResponse = await response.json();
    return this.setSession(data, payload.email, payload.phone);
  }

  private setSession(data: TokenResponse, email: string, phone?: string): User {
    this.token.set(data.access_token);
    localStorage.setItem(this.TOKEN_KEY, data.access_token);

    const user: User = {
      id: data.user_id,
      email,
      full_name: data.full_name,
      role: data.role as 'client' | 'agent' | 'admin',
      phone,
    };

    this.currentUser.set(user);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    return user;
  }

  logout(): void {
    this.token.set(null);
    this.currentUser.set(null);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.USER_KEY);
    }
    this.router.navigate(['/login']);
  }

  navigateToDashboard(): void {
    const role = this.userRole();
    if (role === 'admin') {
      this.router.navigate(['/admin']);
    } else if (role === 'agent') {
      this.router.navigate(['/agent']);
    } else {
      this.router.navigate(['/client']);
    }
  }
}
