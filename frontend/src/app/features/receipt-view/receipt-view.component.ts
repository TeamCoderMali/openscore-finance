import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { ToastService } from '../../core/services/toast.service';
import { SvgIconComponent } from '../../shared/components/svg-icon/svg-icon.component';
import { OsfLogoComponent } from '../../shared/components/osf-logo/osf-logo.component';
import { SpinnerComponent } from '../../shared/components/spinner/spinner.component';
import { ReceiptData } from '../../shared/models/application.model';

@Component({
  selector: 'app-receipt-view',
  standalone: true,
  imports: [CommonModule, SvgIconComponent, OsfLogoComponent, SpinnerComponent],
  templateUrl: './receipt-view.component.html',
  styleUrls: ['./receipt-view.component.css'],
})
export class ReceiptViewComponent implements OnInit {
  receipt = signal<ReceiptData | null>(null);
  loading = signal(true);
  error = signal('');
  printDate = new Date().toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric'
  });

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService,
    private toast: ToastService,
  ) {}

  ngOnInit(): void {
    const appId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadReceipt(appId);
  }

  async loadReceipt(appId: number): Promise<void> {
    try {
      const data = await this.api.getReceipt(appId);
      this.receipt.set(data);
      this.toast.info('Bordereau genere', `Recepisse officiel ${data.receipt_id} pret.`);
    } catch (e: any) {
      this.error.set(e.message);
      this.toast.error('Erreur recepisse', e.message);
    } finally {
      this.loading.set(false);
    }
  }

  print(): void {
    window.print();
  }

  goBack(): void {
    window.history.back();
  }

  getDecisionLabel(decision: string): string {
    switch (decision) {
      case 'approved': return 'ACCORDE';
      case 'adjusted': return 'MONTANT AJUSTE';
      case 'rejected': return 'NON ELIGIBLE';
      default: return decision.toUpperCase();
    }
  }

  formatAmount(amount: number): string {
    return amount.toLocaleString('fr-FR');
  }
}
