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
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) : null,
    );
  }

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
      default: return Icons.description_rounded;
    }
  }

  Color get sectorColor {
    switch (activitySector.toLowerCase()) {
      case 'commerce': return AppTheme.primaryBlue;
      case 'agriculture': return AppTheme.emerald;
      case 'artisanat': return AppTheme.amber;
      case 'tpe': return AppTheme.purple;
      default: return AppTheme.slate500;
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

  String get actionLabel => action.replaceAll('_', ' ').toUpperCase();
}
