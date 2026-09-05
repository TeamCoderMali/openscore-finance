import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SvgIconComponent } from '../../../../shared/components/svg-icon/svg-icon.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { AuditLog } from '../../../../shared/models/application.model';

@Component({
  selector: 'app-admin-audit',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgIconComponent, SpinnerComponent],
  templateUrl: './admin-audit.component.html',
})
export class AdminAuditComponent implements OnInit {
  auditLogs = signal<AuditLog[]>([]);
  auditLoading = signal<boolean>(false);
  auditActionFilter = signal<string>('all');
  auditSearchQuery = signal<string>('');

  filteredAuditLogs = computed(() => {
    let list = this.auditLogs();
    const action = this.auditActionFilter();
    const q = this.auditSearchQuery().toLowerCase().trim();

    if (action !== 'all') {
      list = list.filter(l => l.action.toLowerCase().includes(action.toLowerCase()));
    }
    if (q) {
      list = list.filter(l =>
        l.action.toLowerCase().includes(q) ||
        (l.user_name && l.user_name.toLowerCase().includes(q)) ||
        (l.details && JSON.stringify(l.details).toLowerCase().includes(q))
      );
    }
    return list;
  });

  auditPage = signal<number>(1);
  auditPageSize = signal<number>(10);
  pagedAuditLogs = computed(() => {
    const start = (this.auditPage() - 1) * this.auditPageSize();
    return this.filteredAuditLogs().slice(start, start + this.auditPageSize());
  });
  totalAuditPages = computed(() => Math.max(1, Math.ceil(this.filteredAuditLogs().length / this.auditPageSize())));

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadAuditLogs();
  }

  async loadAuditLogs(): Promise<void> {
    this.auditLoading.set(true);
    try {
      const res = await this.api.getGlobalAuditLogs(100);
      this.auditLogs.set(res.logs);
    } catch (e: any) {
      this.toast.error('Erreur Audit', e.message);
    } finally {
      this.auditLoading.set(false);
    }
  }

  exportAuditTrail(): void {
    const data = JSON.stringify(this.filteredAuditLogs(), null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `openscore-audit-trail-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    this.toast.success('Piste d\'Audit Exportée', 'Le fichier JSON de traçabilité a été téléchargé.');
  }
}
