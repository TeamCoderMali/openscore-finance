import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-spinner',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './spinner.component.html',
  styleUrls: ['./spinner.component.css'],
})
export class SpinnerComponent {
  @Input() size: 'sm' | 'md' | 'lg' | 'fullscreen' = 'md';
  @Input() label: string = '';
  @Input() sublabel: string = '';
  @Input() variant: 'primary' | 'emerald' | 'amber' | 'white' = 'primary';
  @Input() inline: boolean = false;

  getRingColor(): string {
    switch (this.variant) {
      case 'emerald':
        return 'border-emerald-700 border-t-transparent';
      case 'amber':
        return 'border-amber-700 border-t-transparent';
      case 'white':
        return 'border-white border-t-transparent';
      case 'primary':
      default:
        return 'border-blue-900 border-t-transparent';
    }
  }

  getTextColor(): string {
    switch (this.variant) {
      case 'white':
        return 'text-white';
      case 'emerald':
        return 'text-emerald-800';
      case 'amber':
        return 'text-amber-800';
      case 'primary':
      default:
        return 'text-zinc-800';
    }
  }
}
