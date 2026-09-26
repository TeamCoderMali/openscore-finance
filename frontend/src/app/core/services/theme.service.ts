import { Injectable, signal, effect } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly THEME_KEY = 'osf_theme_mode';

  isDarkMode = signal<boolean>(this.getInitialTheme());

  constructor() {
    // Apply theme whenever signal changes
    effect(() => {
      const dark = this.isDarkMode();
      if (typeof document !== 'undefined') {
        if (dark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(this.THEME_KEY, dark ? 'dark' : 'light');
      }
    });
  }

  private getInitialTheme(): boolean {
    if (typeof localStorage !== 'undefined') {
      const saved = localStorage.getItem(this.THEME_KEY);
      if (saved === 'dark') return true;
      if (saved === 'light') return false;
    }
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  }

  toggleDarkMode(): void {
    this.isDarkMode.update(d => !d);
  }

  setDarkMode(dark: boolean): void {
    this.isDarkMode.set(dark);
  }
}
