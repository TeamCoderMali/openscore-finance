import { Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { ToastService } from './toast.service';
import { ApplicationCreateRequest, DraftApplication } from '../../shared/models/application.model';

@Injectable({ providedIn: 'root' })
export class OfflineSyncService {
  private readonly DB_NAME = 'openscore_offline_db';
  private readonly STORE_NAME = 'draft_applications';
  private readonly DB_VERSION = 1;
  private db: IDBDatabase | null = null;

  isOnline = signal<boolean>(typeof navigator !== 'undefined' ? navigator.onLine : true);
  pendingCount = signal<number>(0);
  isSyncing = signal<boolean>(false);

  constructor(private toast: ToastService) {
    this.initIndexedDB().then(() => {
      this.refreshPendingCount();
    });
    this.setupNetworkListeners();
  }

  private async initIndexedDB(): Promise<void> {
    if (typeof indexedDB === 'undefined') return;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.STORE_NAME)) {
          db.createObjectStore(this.STORE_NAME, { keyPath: 'id' });
        }
      };

      request.onsuccess = (event) => {
        this.db = (event.target as IDBOpenDBRequest).result;
        resolve();
      };

      request.onerror = (event) => {
        console.error('IndexedDB init error:', event);
        reject(event);
      };
    });
  }

  private setupNetworkListeners(): void {
    if (typeof window === 'undefined') return;

    window.addEventListener('online', () => {
      this.isOnline.set(true);
      this.toast.info('Connexion rétablie', 'Synchronisation automatique des dossiers hors-ligne en cours...');
      this.syncPendingApplications();
    });

    window.addEventListener('offline', () => {
      this.isOnline.set(false);
      this.toast.warning('Mode Hors-Ligne activé', 'Les demandes de crédit seront sauvegardées localement (IndexedDB).');
    });
  }

  /** Save a draft credit application into IndexedDB */
  async saveDraft(data: ApplicationCreateRequest): Promise<string> {
    await this.ensureDb();
    const id = `draft_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const draft: DraftApplication = {
      id,
      activity_sector: data.activity_sector,
      requested_amount: data.requested_amount,
      requested_duration_months: data.requested_duration_months,
      business_description: data.business_description,
      created_at: new Date().toISOString(),
      status: 'offline_pending',
      sync_attempts: 0,
    };

    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('IndexedDB not initialized'));
        return;
      }
      const transaction = this.db.transaction([this.STORE_NAME], 'readwrite');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.put(draft);

      request.onsuccess = () => {
        this.refreshPendingCount();
        this.toast.warning(
          'Dossier sauvegardé localement',
          `Montant : ${data.requested_amount.toLocaleString('fr-FR')} FCFA. En attente de reconnexion.`
        );
        resolve(id);
      };

      request.onerror = (e) => reject(e);
    });
  }

  /** Retrieve all pending drafts */
  async getDrafts(): Promise<DraftApplication[]> {
    await this.ensureDb();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve([]);
        return;
      }
      const transaction = this.db.transaction([this.STORE_NAME], 'readonly');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result || []);
      request.onerror = (e) => reject(e);
    });
  }

  /** Delete a synchronized draft */
  async deleteDraft(id: string): Promise<void> {
    await this.ensureDb();
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }
      const transaction = this.db.transaction([this.STORE_NAME], 'readwrite');
      const store = transaction.objectStore(this.STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => {
        this.refreshPendingCount();
        resolve();
      };
      request.onerror = (e) => reject(e);
    });
  }

  /** Refresh count of offline drafts */
  async refreshPendingCount(): Promise<void> {
    try {
      const drafts = await this.getDrafts();
      this.pendingCount.set(drafts.length);
    } catch {
      this.pendingCount.set(0);
    }
  }

  /** Synchronize pending drafts to server when online */
  async syncPendingApplications(): Promise<number> {
    if (!navigator.onLine || this.isSyncing()) return 0;

    this.isSyncing.set(true);
    const drafts = await this.getDrafts();
    let syncedCount = 0;

    for (const draft of drafts) {
      try {
        const token = localStorage.getItem('osf_token');
        const response = await fetch(`${environment.apiUrl}/applications`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            activity_sector: draft.activity_sector,
            requested_amount: draft.requested_amount,
            requested_duration_months: draft.requested_duration_months,
            business_description: draft.business_description,
          }),
        });

        if (response.ok) {
          if (draft.id) {
            await this.deleteDraft(draft.id);
          }
          syncedCount++;
        }
      } catch (err) {
        console.warn('Sync attempt failed for draft:', draft.id, err);
      }
    }

    this.isSyncing.set(false);
    await this.refreshPendingCount();

    if (syncedCount > 0) {
      this.toast.success(
        'Synchronisation terminée',
        `${syncedCount} dossier(s) hors-ligne transmis avec succès au serveur.`
      );
    }

    return syncedCount;
  }

  private async ensureDb(): Promise<void> {
    if (!this.db) {
      await this.initIndexedDB();
    }
  }
}
