import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-osf-logo',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './osf-logo.component.html',
  styleUrls: ['./osf-logo.component.css'],
})
export class OsfLogoComponent {
  @Input() variant: 'full' | 'compact' | 'icon' = 'full';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() subtitle: string = 'FINANCE & SCORING';
}
