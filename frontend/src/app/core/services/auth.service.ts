import { Injectable, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { TokenResponse, User } from '../../shared/models/application.model';
import { ApiService } from './api.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'osf_token';
  private readonly USER_KEY = 'osf_user';

  /** Reactive state */
  currentUser = signal<TokenResponse | null>(this._loadUser());
  isAuthenticated = computed(() => this.currentUser() !== null);
  userRole = computed(() => this.currentUser()?.role ?? null);
  userName = computed(() => this.currentUser()?.full_name ?? '');

  constructor(private router: Router) {}

  /** Login: call API then store token */
  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await fetch('http://localhost:8000/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erreur de connexion');
    }

    const data: TokenResponse = await response.json();
    this._saveUser(data);
    this.currentUser.set(data);
    return data;
  }

  /** Logout: clear storage and redirect */
  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUser.set(null);
    this.router.navigate(['/login']);
  }

  /** Get stored JWT token */
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /** Navigate to correct dashboard based on role */
  navigateToDashboard(): void {
    const role = this.userRole();
    if (role === 'agent') {
      this.router.navigate(['/agent']);
    } else if (role === 'client') {
      this.router.navigate(['/client']);
    } else {
      this.router.navigate(['/login']);
    }
  }

  private _saveUser(data: TokenResponse): void {
    localStorage.setItem(this.TOKEN_KEY, data.access_token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(data));
  }

  private _loadUser(): TokenResponse | null {
    const raw = localStorage.getItem(this.USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
}
