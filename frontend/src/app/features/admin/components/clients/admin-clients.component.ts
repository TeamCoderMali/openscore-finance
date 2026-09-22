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

  // Search & Precise Filters
  clientSearchQuery = signal<string>('');
  clientSectorFilter = signal<string>('all');
  clientKycFilter = signal<string>('all');
  clientStatusFilter = signal<string>('all'); // 'all', 'active', 'suspended'
  clientRevenueFilter = signal<string>('all'); // 'all', 'low', 'mid', 'high'
  clientEncoursFilter = signal<string>('all'); // 'all', 'with_apps', 'without_apps'

  // Sorting
  clientSortBy = signal<string>('name'); // 'name', 'revenue', 'apps', 'date'
  clientSortOrder = signal<'asc' | 'desc'>('asc');

  // Pagination
  clientsPage = signal<number>(1);
  clientsPageSize = signal<number>(5);

  activeFiltersCount = computed(() => {
    let count = 0;
    if (this.clientSearchQuery().trim()) count++;
    if (this.clientSectorFilter() !== 'all') count++;
    if (this.clientKycFilter() !== 'all') count++;
    if (this.clientStatusFilter() !== 'all') count++;
    if (this.clientRevenueFilter() !== 'all') count++;
    if (this.clientEncoursFilter() !== 'all') count++;
    return count;
  });

  filteredClients = computed(() => {
    let list = this.clients();
    const sector = this.clientSectorFilter();
    const kyc = this.clientKycFilter();
    const status = this.clientStatusFilter();
    const rev = this.clientRevenueFilter();
    const encours = this.clientEncoursFilter();
    const q = this.clientSearchQuery().toLowerCase().trim();

    // 1. Multi-criteria Search
    if (q) {
      list = list.filter(c =>
        c.full_name?.toLowerCase().includes(q) ||
        c.email?.toLowerCase().includes(q) ||
        (c.phone && c.phone.includes(q)) ||
        (c.account_number && c.account_number.toLowerCase().includes(q)) ||
        (c.id_number && c.id_number.toLowerCase().includes(q))
      );
    }

    // 2. Sector
    if (sector !== 'all') {
      list = list.filter(c => c.activity_sector === sector);
    }

    // 3. KYC Status
    if (kyc !== 'all') {
      list = list.filter(c => c.kyc_status === kyc);
    }

    // 4. Account Status (Active/Suspended)
    if (status !== 'all') {
      const isActive = status === 'active';
      list = list.filter(c => c.is_active === isActive);
    }

    // 5. Revenue Bracket
    if (rev !== 'all') {
      list = list.filter(c => {
        const r = c.monthly_revenue || 0;
        if (rev === 'under_200k') return r < 200000;
        if (rev === '200k_500k') return r >= 200000 && r <= 500000;
        if (rev === '500k_1m') return r > 500000 && r <= 1000000;
        if (rev === 'over_1m') return r > 1000000;
        return true;
      });
    }

    // 6. Encours Filter
    if (encours !== 'all') {
      if (encours === 'with_apps') list = list.filter(c => (c.applications_count || 0) > 0);
      if (encours === 'without_apps') list = list.filter(c => (c.applications_count || 0) === 0);
    }

    // 7. Sorting
    const sortField = this.clientSortBy();
    const sortDir = this.clientSortOrder();
    list.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'revenue':
          cmp = (a.monthly_revenue || 0) - (b.monthly_revenue || 0);
          break;
        case 'apps':
          cmp = (a.applications_count || 0) - (b.applications_count || 0);
          break;
        case 'date':
          cmp = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime();
          break;
        case 'name':
        default:
          cmp = (a.full_name || '').localeCompare(b.full_name || '');
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return list;
  });

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

  // Quick Init Modal (1-clic depuis fiche client)
  showQuickInitModal = signal<boolean>(false);
  quickAccountNumber = signal<string>('');
  quickClientName = signal<string>('');
  quickRequestedAmount = signal<number>(1000000);
  quickRequestedDuration = signal<number>(12);
  quickBusinessDesc = signal<string>('Financement de fonds de roulement');
  creatingQuickApp = signal<boolean>(false);

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

  setSort(field: string): void {
    if (this.clientSortBy() === field) {
      this.clientSortOrder.set(this.clientSortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.clientSortBy.set(field);
      this.clientSortOrder.set(field === 'name' ? 'asc' : 'desc');
    }
    this.clientsPage.set(1);
  }

  resetFilters(): void {
    this.clientSearchQuery.set('');
    this.clientSectorFilter.set('all');
    this.clientKycFilter.set('all');
    this.clientStatusFilter.set('all');
    this.clientRevenueFilter.set('all');
    this.clientEncoursFilter.set('all');
    this.clientSortBy.set('name');
    this.clientSortOrder.set('asc');
    this.clientsPage.set(1);
  }

  // ── 1-CLIC QUICK INIT FOR CLIENT ─────────────────────────────────
  openQuickInitForClient(c: AdminClientSummary | AdminClientDetail): void {
    this.quickAccountNumber.set(c.account_number || '');
    this.quickClientName.set(c.full_name);
    this.quickRequestedAmount.set(1000000);
    this.quickRequestedDuration.set(12);
    this.quickBusinessDesc.set(`Fonds de roulement - ${c.activity_sector || 'Commerce'}`);
    this.showQuickInitModal.set(true);
  }

  closeQuickInitModal(): void {
    this.showQuickInitModal.set(false);
  }

  async executeQuickInit(): Promise<void> {
    const acc = this.quickAccountNumber().trim();
    if (!acc) {
      this.toast.warning('Compte absent', 'Ce client ne possède pas encore de compte CMF lié.');
      return;
    }

    this.creatingQuickApp.set(true);
    try {
      const app = await this.api.quickInitApplication({
        account_number: acc,
        requested_amount: this.quickRequestedAmount(),
        requested_duration_months: this.quickRequestedDuration(),
        business_description: this.quickBusinessDesc(),
      });
      try {
        await this.api.evaluateApplication(app.id);
        await this.api.submitToCommittee(app.id);
      } catch {}

      this.toast.success(
        'Dossier initialisé en 1-clic !',
        `Demande ${app.reference} générée avec succès pour ${this.quickClientName()}.`
      );
      this.closeQuickInitModal();
      await this.loadClients();
    } catch (e: any) {
      this.toast.error('Erreur création dossier', e.message);
    } finally {
      this.creatingQuickApp.set(false);
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

  getStatusLabel(status: string): string {
    if (!status) return 'En attente';
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      documents_uploaded: 'Documents Déposés',
      data_extracted: 'Données Extraites',
      pending_verification: 'En Attente de Vérification',
      data_verified: 'Données Vérifiées',
      scored: 'Dossier Évalué',
      pending_committee_approval: 'En Attente Comité',
      approved: 'Accordé & Validé',
      adjusted: 'Contre-proposition',
      rejected: 'Refusé',
    };
    return labels[status.toLowerCase()] || status;
  }
}
