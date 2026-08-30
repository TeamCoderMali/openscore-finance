import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { OfflineSyncService } from '../services/offline-sync.service';
import { ToastService } from '../services/toast.service';

export const networkInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const offlineSync = inject(OfflineSyncService);
  const toast = inject(ToastService);

  // If browser is offline when making a POST to /applications
  if (!navigator.onLine && req.method === 'POST' && req.url.includes('/applications') && !req.url.includes('/extract-docs')) {
    const payload = req.body as any;
    if (payload && payload.requested_amount) {
      offlineSync.saveDraft(payload);
      toast.warning(
        'Connexion perdue',
        'Votre dossier a été sauvegardé localement en toute sécurité. Il sera synchronisé dès le retour du réseau.'
      );
    }
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Network disconnect error (0 status or net::ERR_CONNECTION_REFUSED / failed to fetch)
      if (error.status === 0 || !navigator.onLine) {
        if (req.method === 'POST' && req.url.includes('/applications') && !req.url.includes('/extract-docs')) {
          const payload = req.body as any;
          if (payload && payload.requested_amount) {
            offlineSync.saveDraft(payload);
            toast.warning(
              'Connexion perdue',
              'Dossier sauvegardé localement (IndexedDB).'
            );
          }
        }
      }
      return throwError(() => error);
    })
  );
};
