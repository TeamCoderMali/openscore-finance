import { Component, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from './core/services/auth.service';
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
  isAuthenticated = computed(() => this.auth.isAuthenticated());
  userRole = computed(() => this.auth.userRole());
  userName = computed(() => this.auth.userName());

  constructor(public auth: AuthService) {}

  logout(): void {
    this.auth.logout();
  }
}
