import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface AmortizationRow {
  month: number;
  payment: number;
  principal: number;
  interest: number;
  insurance: number;
  remainingBalance: number;
}

@Component({
  selector: 'app-agent-simulator',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './agent-simulator.component.html',
})
export class AgentSimulatorComponent {
  // Inputs
  simAmount = signal<number>(1000000);
  simDuration = signal<number>(12);
  simMonthlyRate = signal<number>(1.5);   // 1.5% per month (norme BCEAO)
  simGraceMonths = signal<number>(0);     // Différé d'amortissement
  simInsuranceRate = signal<number>(0.1); // 0.1% insurance

  // Pagination for table
  schedulePage = signal<number>(1);
  schedulePageSize = signal<number>(6);

  // Computed Amortization Schedule
  amortizationSchedule = computed<AmortizationRow[]>(() => {
    const P = this.simAmount();
    const n = this.simDuration();
    const r = (this.simMonthlyRate() / 100);
    const insRate = (this.simInsuranceRate() / 100);
    const grace = this.simGraceMonths();

    const schedule: AmortizationRow[] = [];
    let balance = P;

    const amortizingMonths = Math.max(1, n - grace);
    const monthlyPayment = r > 0
      ? (balance * r * Math.pow(1 + r, amortizingMonths)) / (Math.pow(1 + r, amortizingMonths) - 1)
      : balance / amortizingMonths;

    for (let m = 1; m <= n; m++) {
      const insurance = balance * insRate;
      let interest = balance * r;
      let principal = 0;
      let payment = 0;

      if (m <= grace) {
        // Grace period: pay only interest and insurance
        principal = 0;
        payment = interest + insurance;
      } else {
        principal = Math.min(balance, monthlyPayment - interest);
        interest = Math.max(0, monthlyPayment - principal);
        payment = principal + interest + insurance;
        balance -= principal;
      }

      schedule.push({
        month: m,
        payment: Math.round(payment),
        principal: Math.round(principal),
        interest: Math.round(interest),
        insurance: Math.round(insurance),
        remainingBalance: Math.max(0, Math.round(balance)),
      });
    }

    return schedule;
  });

  pagedAmortizationSchedule = computed(() => {
    const start = (this.schedulePage() - 1) * this.schedulePageSize();
    return this.amortizationSchedule().slice(start, start + this.schedulePageSize());
  });

  totalSchedulePages = computed(() => Math.max(1, Math.ceil(this.amortizationSchedule().length / this.schedulePageSize())));

  totalSimCost = computed(() => {
    const totalPayments = this.amortizationSchedule().reduce((acc, r) => acc + r.payment, 0);
    const totalInterest = this.amortizationSchedule().reduce((acc, r) => acc + r.interest, 0);
    const totalInsurance = this.amortizationSchedule().reduce((acc, r) => acc + r.insurance, 0);
    return { totalPayments, totalInterest, totalInsurance };
  });

  formatAmount(amount: number): string {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  }
}
