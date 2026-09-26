import { Component, EventEmitter, Input, Output, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SvgIconComponent } from '../svg-icon/svg-icon.component';
import { ApiService } from '../../../core/services/api.service';
import { ToastService } from '../../../core/services/toast.service';
import { VoiceQueryResponse } from '../../models/application.model';

@Component({
  selector: 'app-voice-assistant',
  standalone: true,
  imports: [CommonModule, SvgIconComponent],
  templateUrl: './voice-assistant.component.html',
  styleUrls: ['./voice-assistant.component.css'],
})
export class VoiceAssistantComponent implements OnDestroy {
  @Input() placeholder: string = 'Appuyez pour parler en Français ou Bambara...';
  @Input() compact: boolean = false;
  @Output() transcriptEvent = new EventEmitter<string>();
  @Output() detectedFieldEvent = new EventEmitter<{ field: string; value: any }>();
  @Output() responseEvent = new EventEmitter<VoiceQueryResponse>();

  isRecording = signal<boolean>(false);
  isProcessing = signal<boolean>(false);
  transcript = signal<string>('');
  language = signal<'fr' | 'bm'>('fr');
  response = signal<VoiceQueryResponse | null>(null);
  hasSpeechApi = signal<boolean>(false);

  private recognition: any = null;

  constructor(
    private api: ApiService,
    private toast: ToastService,
  ) {
    this.initSpeechRecognition();
  }

  private initSpeechRecognition(): void {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.hasSpeechApi.set(true);
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'fr-FR';

        this.recognition.onresult = (event: any) => {
          let currentTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          this.transcript.set(currentTranscript);
          this.transcriptEvent.emit(currentTranscript);
        };

        this.recognition.onerror = (event: any) => {
          console.warn('Speech recognition error:', event.error);
          this.stopRecording();
          if (event.error !== 'no-speech') {
            this.runMockRecognition();
          }
        };

        this.recognition.onend = () => {
          if (this.isRecording()) {
            this.finishRecording();
          }
        };
      }
    }
  }

  toggleRecording(): void {
    if (this.isRecording()) {
      this.stopRecording();
      this.finishRecording();
    } else {
      this.startRecording();
    }
  }

  startRecording(): void {
    this.isRecording.set(true);
    this.transcript.set('');
    this.response.set(null);
    this.toast.info('Microphone activé', 'Parlez distinctement (Français / Bambara)...');

    if (this.recognition && this.hasSpeechApi()) {
      try {
        this.recognition.start();
      } catch {
        this.runMockRecognition();
      }
    } else {
      this.runMockRecognition();
    }
  }

  stopRecording(): void {
    this.isRecording.set(false);
    if (this.recognition && this.hasSpeechApi()) {
      try {
        this.recognition.stop();
      } catch {
        // Ignore
      }
    }
  }

  private runMockRecognition(): void {
    // Simulated realistic query options for local Malian market demo
    const mockQueries = [
      'Je veux un crédit pour mon commerce de tissus et bazin au Grand Marché de Bamako',
      'N b\'a fɛ ka wari ta n ka sugu baara kama (Sugu - Commerce)',
      'Culture maraîchère à Baguinéda, besoin de 750 000 FCFA pour la saison des pluies (Sɛnɛ)',
      'Atelier de couture et broderie traditionnelle à Médina Coura (Numuya)',
      'Quels documents dois-je fournir pour valider mon dossier NINA ?',
    ];
    const picked = mockQueries[Math.floor(Math.random() * mockQueries.length)];

    setTimeout(() => {
      if (this.isRecording()) {
        this.transcript.set(picked);
        this.transcriptEvent.emit(picked);
        this.stopRecording();
        this.finishRecording();
      }
    }, 2800);
  }

  async finishRecording(): Promise<void> {
    const text = this.transcript();
    if (!text) return;

    this.isProcessing.set(true);
    try {
      // Analyze local keywords
      this.detectLocalKeywords(text);

      // Call Backend Voice Query API
      const res = await this.api.voiceQuery(text, this.language());
      this.response.set(res);
      this.responseEvent.emit(res);

      if (res.suggested_field) {
        this.detectedFieldEvent.emit(res.suggested_field);
      }

      // Voice synthesis response in French if available
      this.speakText(res.response_text);
    } catch (e: any) {
      this.toast.error('Assistant vocal', e.message || 'Erreur lors du traitement de la requête');
    } finally {
      this.isProcessing.set(false);
    }
  }

  private detectLocalKeywords(text: string): void {
    const lower = text.toLowerCase();

    // Sugu -> Commerce
    if (lower.includes('sugu') || lower.includes('marché') || lower.includes('commerce') || lower.includes('bazin')) {
      this.detectedFieldEvent.emit({ field: 'activity_sector', value: 'Commerce' });
      this.toast.info('Secteur détecté', 'Commerce de détail / Grand Marché (Sugu)');
    }
    // Sɛnɛ / Foro -> Agriculture
    else if (lower.includes('sɛnɛ') || lower.includes('sene') || lower.includes('foro') || lower.includes('maraîch')) {
      this.detectedFieldEvent.emit({ field: 'activity_sector', value: 'Agriculture' });
      this.toast.info('Secteur détecté', 'Agriculture / Maraîchage (Sɛnɛ)');
    }
    // Numuya -> Artisanat
    else if (lower.includes('numuya') || lower.includes('couture') || lower.includes('atelier') || lower.includes('artisan')) {
      this.detectedFieldEvent.emit({ field: 'activity_sector', value: 'Artisanat' });
      this.toast.info('Secteur détecté', 'Artisanat / Atelier (Numuya)');
    }

    // Amount detection (e.g. 500 000, 750 000, 1 500 000)
    const amountMatch = text.match(/\b(\d{1,3}(?:[\s\.]\d{3})+|\d{5,8})\b/);
    if (amountMatch) {
      const cleanNum = parseFloat(amountMatch[0].replace(/[\s\.]/g, ''));
      if (cleanNum >= 50000 && cleanNum <= 10000000) {
        this.detectedFieldEvent.emit({ field: 'requested_amount', value: cleanNum });
        this.toast.info('Montant détecté', `${cleanNum.toLocaleString('fr-FR')} FCFA`);
      }
    }
  }

  private speakText(text: string): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'fr-FR';
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
      } catch {
        // Ignore audio playback constraints
      }
    }
  }

  setLanguage(lang: 'fr' | 'bm'): void {
    this.language.set(lang);
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }
}
