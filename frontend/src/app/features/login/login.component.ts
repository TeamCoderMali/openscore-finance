import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
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
  isRegisterMode = signal<boolean>(false);

  // Login fields
  email = '';
  password = '';

  // Register fields
  fullName = '';
  regEmail = '';
  regPassword = '';
  regPhone = '';
  regIdNumber = '';
  regCity = 'Bamako';
  regActivitySector = 'Commerce';
  regMonthlyRevenue: number | null = 450000;
  regMonthlyExpenses: number | null = 150000;
  regExistingDebt: number | null = 0;
  regYearsInBusiness: number | null = 3;
  regRevenueRegularityMonths: number | null = 12;
  regRequestedAmount: number | null = 750000;
  regBusinessDescription = '';

  error = signal<string>('');
  loading = signal<boolean>(false);
  isDarkMode = computed(() => this.theme.isDarkMode());

  demoUsers = [
    {
      role: 'client',
      label: 'Amadou Diallo',
      subtitle: 'Commerce • Grand Marché',
      email: 'amadou.diallo@mail.ml',
      pass: 'password123'
    },
    {
      role: 'client',
      label: 'Fatoumata Traoré',
      subtitle: 'Agriculture • Baguinéda',
      email: 'fatoumata.traore@mail.ml',
      pass: 'password123'
    },
    {
      role: 'agent',
      label: 'Ibrahima Coulibaly',
      subtitle: 'Agent CIF / IMF',
      email: 'agent@openscore.ml',
      pass: 'agent123'
    },
    {
      role: 'agent',
      label: 'Awa Sangaré',
      subtitle: 'Agent CIF / IMF',
      email: 'awa.sangare@openscore.ml',
      pass: 'agent123'
    },
    {
      role: 'admin',
      label: 'Fatoumata Cissé',
      subtitle: 'Direction Générale • Super Admin',
      email: 'admin@openscore.ml',
      pass: 'admin123'
    },
  ];

  constructor(
    private auth: AuthService,
    public theme: ThemeService,
    private router: Router,
    private toast: ToastService,
  ) {
    if (this.auth.isAuthenticated()) {
      this.auth.navigateToDashboard();
    }
  }

  toggleDarkMode(): void {
    this.theme.toggleDarkMode();
  }

  fillDemo(email: string, pass: string): void {
    this.isRegisterMode.set(false);
    this.email = email;
    this.password = pass;
    this.toast.info('Identifiants chargés', `Compte ${email.includes('agent') ? 'Agent CIF/IMF' : 'Client Emprunteur'} prêt.`);
  }

  async onSubmit(): Promise<void> {
    if (this.isRegisterMode()) {
      await this.handleRegister();
    } else {
      await this.handleLogin();
    }
  }

  private async handleLogin(): Promise<void> {
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
        'Connexion réussie',
        `Bienvenue ${user.full_name} (${user.role === 'agent' ? 'Agent CIF/IMF' : 'Client Emprunteur'})`
      );
      this.auth.navigateToDashboard();
    } catch (e: any) {
      const msg = e.message || 'Identifiants invalides';
      this.error.set(msg);
      this.toast.error('Échec d\'authentification', msg);
    } finally {
      this.loading.set(false);
    }
  }

  private async handleRegister(): Promise<void> {
    if (!this.fullName || !this.regEmail || !this.regPassword) {
      this.error.set('Veuillez remplir tous les champs obligatoires (Nom, Email, Mot de passe)');
      this.toast.warning('Formulaire incomplet', 'Nom, email et mot de passe sont requis.');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    try {
      const user = await this.auth.register({
        fullName: this.fullName,
        email: this.regEmail,
        password: this.regPassword,
        phone: this.regPhone,
        idNumber: this.regIdNumber,
        city: this.regCity,
        activitySector: this.regActivitySector,
        monthlyRevenue: this.regMonthlyRevenue ? +this.regMonthlyRevenue : 350000,
        monthlyExpenses: this.regMonthlyExpenses ? +this.regMonthlyExpenses : 120000,
        existingDebt: this.regExistingDebt ? +this.regExistingDebt : 0,
        yearsInBusiness: this.regYearsInBusiness ? +this.regYearsInBusiness : 3,
        revenueRegularityMonths: this.regRevenueRegularityMonths ? +this.regRevenueRegularityMonths : 12,
        requestedAmount: this.regRequestedAmount ? +this.regRequestedAmount : 750000,
        businessDescription: this.regBusinessDescription,
      });
      this.toast.success(
        'Compte créé avec succès',
        `Bienvenue ${user.full_name} ! Votre profil financier a été configuré avec succès.`
      );
      this.auth.navigateToDashboard();
    } catch (e: any) {
      const msg = e.message || "Échec de l'inscription";
      this.error.set(msg);
      this.toast.error('Erreur d\'inscription', msg);
    } finally {
      this.loading.set(false);
    }
  }
}
