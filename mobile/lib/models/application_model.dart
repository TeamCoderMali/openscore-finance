import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class Application {
  final int id;
  final String reference;
  final int applicantId;
  final String? applicantName;
  final String activitySector;
  final double requestedAmount;
  final int requestedDurationMonths;
  final String? businessDescription;
  final String status;
  final int? agentId;
  final double? approvedAmount;
  final String? branchCode;
  final String? applicationType;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  Application({
    required this.id,
    required this.reference,
    required this.applicantId,
    this.applicantName,
    required this.activitySector,
    required this.requestedAmount,
    required this.requestedDurationMonths,
    this.businessDescription,
    required this.status,
    this.agentId,
    this.approvedAmount,
    this.branchCode,
    this.applicationType,
    this.createdAt,
    this.updatedAt,
  });

  factory Application.fromJson(Map<String, dynamic> json) {
    return Application(
      id: json['id'] ?? 0,
      reference: json['reference'] ?? '',
      applicantId: json['applicant_id'] ?? 0,
      applicantName: json['applicant_name'],
      activitySector: json['activity_sector'] ?? '',
      requestedAmount: (json['requested_amount'] ?? 0).toDouble(),
      requestedDurationMonths: json['requested_duration_months'] ?? 12,
      businessDescription: json['business_description'],
      status: json['status'] ?? 'draft',
      agentId: json['agent_id'],
      approvedAmount: json['approved_amount'] != null ? (json['approved_amount'] as num).toDouble() : null,
      branchCode: json['branch_code'],
      applicationType: json['application_type'],
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) : null,
    );
  }

  bool get isAdjusted =>
      approvedAmount != null && (approvedAmount! - requestedAmount).abs() > 1;

  double get finalAmount => approvedAmount ?? requestedAmount;

  String get statusLabel {
    final s = status.toLowerCase().replaceAll('applicationstatus.', '').trim();
    switch (s) {
      case 'draft': return 'Brouillon';
      case 'documents_uploaded': return 'Documents Déposés';
      case 'data_extracted': return 'Données Extraites';
      case 'pending_verification': return 'En Attente de Vérification';
      case 'data_verified': return 'Données Vérifiées';
      case 'scored': return 'Dossier Évalué';
      case 'pending_committee_approval': return 'En Attente Comité';
      case 'approved': return 'Approuvé';
      case 'adjusted': return 'Ajusté';
      case 'rejected': return 'Refusé';
      default: return 'En Cours';
    }
  }

  Color get statusColor {
    final s = status.toLowerCase().replaceAll('applicationstatus.', '').trim();
    switch (s) {
      case 'approved': return AppTheme.emerald;
      case 'adjusted': return AppTheme.primaryBlue;
      case 'rejected': return AppTheme.rose;
      case 'pending_verification':
      case 'data_verified':
      case 'pending_committee_approval':
        return AppTheme.amber;
      case 'scored': return AppTheme.purple;
      default: return AppTheme.slate400;
    }
  }

  Color get statusBg {
    final s = status.toLowerCase().replaceAll('applicationstatus.', '').trim();
    switch (s) {
      case 'approved': return AppTheme.emeraldLight;
      case 'adjusted': return const Color(0xFFdbeafe);
      case 'rejected': return AppTheme.roseLight;
      case 'pending_verification':
      case 'data_verified':
      case 'pending_committee_approval':
        return AppTheme.amberLight;
      case 'scored': return AppTheme.purpleLight;
      default: return AppTheme.slate100;
    }
  }

  String get sectorEmoji => '';

  IconData get sectorIcon {
    switch (activitySector.toLowerCase()) {
      case 'commerce': return Icons.storefront_rounded;
      case 'agriculture': return Icons.agriculture_rounded;
      case 'artisanat': return Icons.handyman_rounded;
      case 'tpe': return Icons.business_center_rounded;
      case 'autre': return Icons.category_rounded;
      default: return Icons.description_rounded;
    }
  }

  Color get sectorColor {
    switch (activitySector.toLowerCase()) {
      case 'commerce': return AppTheme.primaryBlue;
      case 'agriculture': return AppTheme.emerald;
      case 'artisanat': return AppTheme.amber;
      case 'tpe': return AppTheme.purple;
      case 'autre': return const Color(0xFF0D9488);
      default: return AppTheme.slate500;
    }
  }
  String get activitySectorLabel {
    switch (activitySector.toLowerCase().trim()) {
      case 'commerce':
      case 'retail':
        return 'Commerce';
      case 'agriculture':
      case 'farming':
        return 'Agriculture';
      case 'artisanat':
      case 'craft':
      case 'crafts':
        return 'Artisanat';
      case 'tpe':
      case 'sme':
      case 'small_business':
        return 'Très Petite Entreprise (TPE)';
      case 'autre':
      case 'other':
        return 'Autre';
      default:
        return activitySector.isNotEmpty ? activitySector : 'Activité Générale';
    }
  }

  String get applicationTypeLabel {
    final t = (applicationType ?? '').toUpperCase().trim();
    switch (t) {
      case 'BUSINESS':
      case 'ENTREPRISE':
      case 'PME':
        return 'Entreprise / PME';
      case 'INDIVIDUAL':
      case 'PARTICULIER':
        return 'Particulier / Activité individuelle';
      case 'SALARIED':
      case 'SALARIÉ':
      case 'SALARIE':
        return 'Salarié du secteur privé';
      case 'CIVIL_SERVANT':
      case 'FONCTIONNAIRE':
        return 'Fonctionnaire d\'État';
      default:
        return 'Particulier / Salarié';
    }
  }
}

class AuditLog {
  final int id;
  final int applicationId;
  final int? userId;
  final String? userName;
  final String action;
  final Map<String, dynamic>? details;
  final DateTime? timestamp;

  AuditLog({
    required this.id,
    required this.applicationId,
    this.userId,
    this.userName,
    required this.action,
    this.details,
    this.timestamp,
  });

  factory AuditLog.fromJson(Map<String, dynamic> json) {
    return AuditLog(
      id: json['id'] ?? 0,
      applicationId: json['application_id'] ?? 0,
      userId: json['user_id'],
      userName: json['user_name'],
      action: json['action'] ?? '',
      details: json['details'] as Map<String, dynamic>?,
      timestamp: json['timestamp'] != null ? DateTime.tryParse(json['timestamp']) : null,
    );
  }

  String get actionLabel {
    final a = action.toLowerCase().trim();
    switch (a) {
      case 'quick_init_created':
        return 'Initialisation rapide du dossier';
      case 'application_created':
        return 'Création de la demande';
      case 'documents_uploaded':
        return 'Documents justificatifs déposés';
      case 'document_extracted':
      case 'data_extracted':
        return 'Extraction automatique OCR';
      case 'data_verified':
        return 'Données financières vérifiées';
      case 'guarantee_added':
        return 'Garantie matérielle enregistrée';
      case 'guarantee_deleted':
        return 'Garantie retirée du dossier';
      case 'debt_added':
        return 'Engagement antérieur déclaré';
      case 'debt_deleted':
        return 'Engagement antérieur supprimé';
      case 'scoring_completed':
        return 'Évaluation & calcul du score';
      case 'counter_proposal_applied':
        return 'Proposition alternative appliquée';
      case 'submitted_to_committee':
        return 'Dossier transmis au comité de crédit';
      case 'committee_decision_approved':
        return 'Crédit accordé par le comité';
      case 'committee_decision_rejected':
        return 'Dossier refusé par le comité';
      case 'committee_decision_adjusted':
        return 'Ajustement proposé par le comité';
      case 'committee_document_requested':
        return 'Pièce complémentaire exigée';
      case 'document_provided_by_agent':
        return 'Pièce complémentaire fournie';
      case 'client_contacted_phone':
        return 'Contact client par téléphone';
      case 'client_contacted_sms':
        return 'Contact client par SMS';
      case 'client_contacted_whatsapp':
        return 'Contact client via WhatsApp';
      case 'client_contacted_email':
        return 'Contact client par email';
      case 'client_contacted_in_person':
        return 'Visite client sur le terrain';
      case 'client_account_registered_with_profile':
        return 'Compte client créé avec profil complet';
      case 'user_created_by_admin':
        return 'Utilisateur créé par l\'administrateur';
      case 'user_deleted_by_admin':
        return 'Utilisateur supprimé';
      case 'scoring_policy_version_created':
        return 'Politique de scoring actualisée';
      case 'client_updated_by_admin':
        return 'Fiche client mise à jour';
      case 'application_reassigned_by_admin':
        return 'Dossier réaffecté';
      case 'password_reset_by_admin':
        return 'Mot de passe réinitialisé';
      case 'branch_created_by_admin':
        return 'Nouvelle agence configurée';
      case 'status_updated':
        return 'Statut du dossier actualisé';
      case 'application_rejected':
        return 'Dossier refusé';
      case 'application_approved':
        return 'Crédit accordé';
      default:
        // French fallback
        String label = action.replaceAll('_', ' ').trim();
        final lower = label.toLowerCase();
        if (lower.contains('init')) return 'Dossier initialisé';
        if (lower.contains('guarantee')) return 'Garantie enregistrée';
        if (lower.contains('debt')) return 'Engagement déclaré';
        if (lower.contains('score') || lower.contains('scoring')) return 'Score calculé';
        if (lower.contains('committee')) return 'Décision du comité';
        if (lower.contains('approved')) return 'Crédit accordé';
        if (lower.contains('rejected')) return 'Dossier refusé';
        if (lower.contains('adjusted')) return 'Ajustement proposé';
        if (lower.contains('document') || lower.contains('doc')) return 'Document mis à jour';
        return label;
    }
  }
}
