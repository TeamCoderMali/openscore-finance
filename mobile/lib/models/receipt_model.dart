class ReceiptData {
  final String reference;
  final String applicantName;
  final String applicantEmail;
  final String? applicantPhone;
  final String activitySector;
  final double requestedAmount;
  final String decision;
  final double? approvedAmount;
  final double? proposedAmount;
  final int? proposedDurationMonths;
  final int score;
  final String riskLevel;
  final String? agentName;
  final String? accountNumber;
  final DateTime? scoredAt;
  final DateTime? createdAt;
  final String receiptId;

  ReceiptData({
    required this.reference,
    required this.applicantName,
    required this.applicantEmail,
    this.applicantPhone,
    required this.activitySector,
    required this.requestedAmount,
    required this.decision,
    this.approvedAmount,
    this.proposedAmount,
    this.proposedDurationMonths,
    required this.score,
    required this.riskLevel,
    this.agentName,
    this.accountNumber,
    this.scoredAt,
    this.createdAt,
    required this.receiptId,
  });

  factory ReceiptData.fromJson(Map<String, dynamic> json) {
    return ReceiptData(
      reference: json['reference'] ?? '',
      applicantName: json['applicant_name'] ?? '',
      applicantEmail: json['applicant_email'] ?? '',
      applicantPhone: json['applicant_phone'],
      activitySector: json['activity_sector'] ?? '',
      requestedAmount: (json['requested_amount'] ?? 0).toDouble(),
      decision: json['decision'] ?? '',
      approvedAmount: json['approved_amount']?.toDouble(),
      proposedAmount: json['proposed_amount']?.toDouble(),
      proposedDurationMonths: json['proposed_duration_months'],
      score: json['score'] ?? 0,
      riskLevel: json['risk_level'] ?? '',
      agentName: json['agent_name'],
      accountNumber: json['account_number'],
      scoredAt: json['scored_at'] != null ? DateTime.tryParse(json['scored_at']) : null,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      receiptId: json['receipt_id'] ?? '',
    );
  }

  String get decisionLabel {
    final d = decision.toLowerCase().replaceAll('applicationstatus.', '').trim();
    switch (d) {
      case 'approved': return 'APPROUVÉ';
      case 'adjusted': return 'AJUSTÉ';
      case 'rejected': return 'REFUSÉ';
      case 'pending_committee_approval': return 'EN ATTENTE COMITÉ';
      case 'scored': return 'ÉVALUÉ';
      case 'pending_verification': return 'EN ATTENTE';
      default: return 'EN COURS';
    }
  }

  String get riskLabel {
    final r = riskLevel.toLowerCase().replaceAll('risklevel.', '').trim();
    switch (r) {
      case 'low': return 'Faible';
      case 'medium': return 'Modéré';
      case 'high': return 'Élevé';
      case 'very_high': return 'Très Élevé';
      case 'critical': return 'Critique';
      default: return r;
    }
  }

  double get finalAmount => approvedAmount ?? proposedAmount ?? requestedAmount;
}
