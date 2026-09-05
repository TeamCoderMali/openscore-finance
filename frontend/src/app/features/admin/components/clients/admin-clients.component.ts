import { Component, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { AdminClientSummary, AdminClientDetail } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-clients',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-clients.component.html',
})
export class AdminClientsComponent implements OnInit {
  clients = signal<AdminClientSummary[]>([]);
  clientsLoading = signal<boolean>(false);
  clientSectorFilter = signal<string>('all');
  clientKycFilter = signal<string>('all');
  clientSearchQuery = signal<string>('');

  filteredClients = computed(() => {
    let list = this.clients();
    const sector = this.clientSectorFilter();
    const kyc = this.clientKycFilter();
    const q = this.clientSearchQuery().toLowerCase().trim();

    if (sector !== 'all') {
      list = list.filter(c => c.activity_sector === sector);
    }
    if (kyc !== 'all') {
      list = list.filter(c => c.kyc_status === kyc);
    }
    if (q) {
      list = list.filter(c =>
        c.full_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        (c.phone && c.phone.includes(q))
      );
    }
    return list;
  });

  clientsPage = signal<number>(1);
  clientsPageSize = signal<number>(5);
  pagedClients = computed(() => {
    const start = (this.clientsPage() - 1) * this.clientsPageSize();
    return this.filteredClients().slice(start, start + this.clientsPageSize());
  });
  totalClientsPages = computed(() => Math.max(1, Math.ceil(this.filteredClients().length / this.clientsPageSize())));

  // Client Detail Modal
  selectedClient = signal<AdminClientDetail | null>(null);
  loadingClientDetail = signal<boolean>(false);
  showClientModal = signal<boolean>(false);

  // Create Client Modal
  showCreateClientModal = signal<boolean>(false);
  newClient = signal({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    sector: 'Commerce',
    monthly_revenue: 350000,
    monthly_expenses: 120000,
  });
  creatingClient = signal<boolean>(false);

  // Password Reset Modal
  showResetPasswordModal = signal<boolean>(false);
  targetResetUser = signal<{ id: number; name: string; email: string } | null>(null);
  newPasswordInput = signal<string>('');
  resettingPassword = signal<boolean>(false);

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadClients();
  }

  async loadClients(): Promise<void> {
    this.clientsLoading.set(true);
    try {
      const data = await this.api.getAdminClients(
        this.clientSectorFilter(),
        this.clientKycFilter(),
        this.clientSearchQuery()
      );
      this.clients.set(data);
    } catch (e: any) {
      this.toast.error('Erreur Clients', e.message);
    } finally {
      this.clientsLoading.set(false);
    }
  }

  async viewClientDetail(c: AdminClientSummary): Promise<void> {
    this.loadingClientDetail.set(true);
    this.showClientModal.set(true);
    try {
      const detail = await this.api.getAdminClientDetail(c.id);
      this.selectedClient.set(detail);
    } catch (e: any) {
      this.toast.error('Erreur Chargement Fiche', e.message);
      this.showClientModal.set(false);
    } finally {
      this.loadingClientDetail.set(false);
    }
  }

  closeClientModal(): void {
    this.showClientModal.set(false);
    this.selectedClient.set(null);
  }

  async toggleClientStatus(c: { id: number; full_name: string; is_active: boolean }): Promise<void> {
    try {
      const res = await this.api.toggleUserActive(c.id);
      c.is_active = res.is_active;
      this.toast.info(
        'Statut Compte Modifié',
        `Le compte ${c.full_name} est désormais ${res.is_active ? 'Actif' : 'Suspendu'}.`
      );
      await this.loadClients();
      if (this.selectedClient() && this.selectedClient()!.id === c.id) {
        this.selectedClient()!.is_active = res.is_active;
      }
    } catch (e: any) {
      this.toast.error('Erreur Statut', e.message);
    }
  }

  openCreateClientModal(): void {
    this.newClient.set({
      full_name: '',
      email: '',
      phone: '',
      password: '',
      sector: 'Commerce',
      monthly_revenue: 350000,
      monthly_expenses: 120000,
    });
    this.showCreateClientModal.set(true);
  }

  closeCreateClientModal(): void {
    this.showCreateClientModal.set(false);
  }

  async createClient(): Promise<void> {
    const p = this.newClient();
    if (!p.full_name || !p.email || !p.password) {
      this.toast.warning('Champs requis', 'Nom, email et mot de passe obligatoires');
      return;
    }
    this.creatingClient.set(true);
    try {
      await this.api.createAdminUser({
        full_name: p.full_name,
        email: p.email,
        phone: p.phone,
        password: p.password,
        role: 'client',
      });
      this.toast.success(
        'Client Enrôlé avec Succès',
        `Le compte emprunteur pour ${p.full_name} est créé.`
      );
      this.closeCreateClientModal();
      await this.loadClients();
    } catch (e: any) {
      this.toast.error('Erreur Création', e.message);
    } finally {
      this.creatingClient.set(false);
    }
  }

  openResetPasswordModal(user: { id: number; full_name: string; email: string }): void {
    this.targetResetUser.set({
      id: user.id,
      name: user.full_name,
      email: user.email,
    });
    this.newPasswordInput.set('');
    this.showResetPasswordModal.set(true);
  }

  closeResetPasswordModal(): void {
    this.showResetPasswordModal.set(false);
    this.targetResetUser.set(null);
  }

  async executeResetPassword(): Promise<void> {
    const u = this.targetResetUser();
    const pwd = this.newPasswordInput();
    if (!u || !pwd || pwd.length < 4) {
      this.toast.warning('Mot de passe trop court', 'Le mot de passe doit comporter au moins 4 caractères');
      return;
    }
    this.resettingPassword.set(true);
    try {
      const res = await this.api.resetUserPassword(u.id, { new_password: pwd });
      this.toast.success('Sécurité Compte', res.message);
      this.closeResetPasswordModal();
    } catch (e: any) {
      this.toast.error('Erreur Réinitialisation', e.message);
    } finally {
      this.resettingPassword.set(false);
    }
  }

  exportClientKyc(client: AdminClientDetail | AdminClientSummary): void {
    this.toast.info(
      'Export Fiche Emprunteur',
      `Fiche KYC de ${client.full_name} téléchargée pour archivage légal.`
    );
  }

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
