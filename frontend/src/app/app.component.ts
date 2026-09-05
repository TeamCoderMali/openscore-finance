import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from './core/services/auth.service';
import { ThemeService } from './core/services/theme.service';
import { OfflineSyncService } from './core/services/offline-sync.service';
import { SvgIconComponent } from './shared/components/svg-icon/svg-icon.component';
import { ToastComponent } from './shared/components/toast/toast.component';
import { OsfLogoComponent } from './shared/components/osf-logo/osf-logo.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterModule, SvgIconComponent, ToastComponent, OsfLogoComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  isSidebarCollapsed = signal<boolean>(false);
  isAuthenticated = computed(() => this.auth.isAuthenticated());
  userRole = computed(() => this.auth.userRole());
  userName = computed(() => this.auth.userName());
  isOnline = computed(() => this.offlineSync.isOnline());
  pendingCount = computed(() => this.offlineSync.pendingCount());
  isDarkMode = computed(() => this.theme.isDarkMode());

  constructor(
    public auth: AuthService,
    public theme: ThemeService,
    public offlineSync: OfflineSyncService,
    private router: Router,
  ) {}

  toggleDarkMode(): void {
    this.theme.toggleDarkMode();
  }

  toggleSidebar(): void {
    this.isSidebarCollapsed.update(c => !c);
  }

  isActive(basePath: string, view?: string): boolean {
    const url = this.router.url;
    if (basePath === '/agent') {
      if (!url.startsWith('/agent')) return false;
      if (view) {
        return url.includes(`/agent/${view}`) || url.includes(`view=${view}`);
      }
      return url === '/agent' || url.includes('/agent/pipeline');
    }
    if (basePath === '/admin') {
      if (!url.startsWith('/admin')) return false;
      if (view) {
        return url.includes(`/admin/${view}`) || url.includes(`view=${view}`);
      }
      return url === '/admin' || url.includes('/admin/overview');
    }
    if (!url.startsWith(basePath)) return false;
    if (!view) {
      return !url.includes('view=') || url.includes('view=applications') || url.includes('view=pipeline') || url.includes('view=overview');
    }
    return url.includes(`view=${view}`);
  }

  syncNow(): void {
    this.offlineSync.syncPendingApplications();
  }

  logout(): void {
    this.auth.logout();
  }
}
