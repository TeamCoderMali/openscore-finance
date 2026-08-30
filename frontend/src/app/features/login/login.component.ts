import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { OsfLogoComponent } from '../../shared/components/osf-logo/osf-logo.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, OsfLogoComponent, SpinnerComponent],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent {
  email = '';
  password = '';
  error = signal<string>('');
  loading = signal(false);

  constructor(
    private auth: AuthService,
    private router: Router,
    private toast: ToastService,
  ) {
    if (this.auth.isAuthenticated()) {
      this.auth.navigateToDashboard();
    }
  }

  fillDemo(email: string, pass: string): void {
    this.email = email;
    this.password = pass;
    this.toast.info('Identifiants charges', `Compte ${email.includes('agent') ? 'Agent' : 'Client'} selectionne.`);
  }

  async onSubmit(): Promise<void> {
    if (!this.email || !this.password) {
      this.error.set('Veuillez renseigner votre email et mot de passe');
      this.toast.warning('Formulaire incomplet', 'Veuillez saisir votre email et votre mot de passe.');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    try {
      const user = await this.auth.login(this.email, this.password);
      this.toast.success(
        'Connexion reussie',
        `Bienvenue ${user.full_name} (${user.role === 'agent' ? 'Agent CIF/IMF' : 'Client'})`
      );
      this.auth.navigateToDashboard();
    } catch (e: any) {
      const msg = e.message || 'Identifiants invalides';
      this.error.set(msg);
      this.toast.error('Echec d\'authentification', msg);
    } finally {
      this.loading.set(false);
    }
  }
}
