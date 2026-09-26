import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, ToastMessage } from '../../../core/services/toast.service';
import { SvgIconComponent } from '../svg-icon/svg-icon.component';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule, SvgIconComponent],
  templateUrl: './toast.component.html',
  styleUrls: ['./toast.component.css'],
})
export class ToastComponent {
  constructor(public toastService: ToastService) {}

  getIcon(type: string): string {
    switch (type) {
      case 'success':
        return 'check-circle';
      case 'error':
        return 'alert';
      case 'warning':
        return 'alert';
      case 'info':
        return 'shield';
      default:
        return 'shield';
    }
  }

  getBorderClass(type: string): string {
    switch (type) {
      case 'success':
        return 'border-l-emerald-600 bg-white text-zinc-900 shadow-sm';
      case 'error':
        return 'border-l-rose-600 bg-white text-zinc-900 shadow-sm';
      case 'warning':
        return 'border-l-amber-600 bg-white text-zinc-900 shadow-sm';
      case 'info':
        return 'border-l-blue-900 bg-white text-zinc-900 shadow-sm';
      default:
        return 'border-l-zinc-600 bg-white text-zinc-900 shadow-sm';
    }
  }

  getIconColorClass(type: string): string {
    switch (type) {
      case 'success':
        return 'text-emerald-700 bg-emerald-50';
      case 'error':
        return 'text-rose-700 bg-rose-50';
      case 'warning':
        return 'text-amber-700 bg-amber-50';
      case 'info':
        return 'text-blue-900 bg-blue-50';
      default:
        return 'text-zinc-700 bg-zinc-100';
    }
  }

  dismiss(toast: ToastMessage): void {
    this.toastService.remove(toast.id);
  }
}
