import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:share_plus/share_plus.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/receipt_model.dart';
import '../../shared/widgets/shared_widgets.dart';

class ReceiptDetailScreen extends StatefulWidget {
  final int applicationId;

  const ReceiptDetailScreen({super.key, required this.applicationId});

  @override
  State<ReceiptDetailScreen> createState() => _ReceiptDetailScreenState();
}

class _ReceiptDetailScreenState extends State<ReceiptDetailScreen> {
  final _api = ApiService();
  ReceiptData? _receipt;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _api.getReceipt(widget.applicationId);
      _receipt = ReceiptData.fromJson(data);
    } catch (e) {
      _error =
          'Récépissé non disponible.\nLe dossier n\'a peut-être pas encore été évalué.';
    }
    if (mounted) setState(() => _loading = false);
  }

  void _share([BuildContext? ctx]) {
    if (_receipt == null) return;
    final targetCtx = ctx ?? context;
    final box = targetCtx.findRenderObject() as RenderBox?;
    final size = MediaQuery.of(targetCtx).size;
    final origin = (box != null && box.hasSize && box.size.width > 0 && box.size.height > 0)
        ? (box.localToGlobal(Offset.zero) & box.size)
        : Rect.fromLTWH(0, 0, size.width, size.height / 2);

    final text = '''
      RÉCÉPISSÉ OFFICIEL — OpenScore Finance Mali
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      Référence  : ${_receipt!.reference}
      Client     : ${_receipt!.applicantName}
      Secteur    : ${_receipt!.activitySector}
      Montant    : ${formatFCFA(_receipt!.requestedAmount)}
      Décision   : ${_receipt!.decisionLabel}
      Score      : ${_receipt!.score}/100
      Risque     : ${_receipt!.riskLabel}
      Compte IMF : ${_receipt!.accountNumber ?? 'Non spécifié'}
      Agent      : ${_receipt!.agentName ?? 'Agent de crédit assermenté'}
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      ID Récépissé : ${_receipt!.receiptId}
      Date : ${formatDate(_receipt!.scoredAt)}

      OpenScore Finance • Microfinance Mali • BCEAO/UEMOA
      ''';
    Share.share(
      text,
      subject: 'Récépissé OpenScore Finance - ${_receipt!.reference}',
      sharePositionOrigin: origin,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Récépissé Officiel',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
        actions: [
          if (_receipt != null)
            Builder(
              builder: (iconContext) => IconButton(
                icon: const Icon(Icons.share_outlined),
                onPressed: () => _share(iconContext),
                tooltip: 'Partager',
              ),
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? EmptyState(
                  message: _error!,
                  icon: Icons.description_outlined,
                  actionLabel: 'Réessayer',
                  onAction: _load,
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      // ── Receipt card ──────────────────────────
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppTheme.slate200),
                          boxShadow: [
                            BoxShadow(
                              color: AppTheme.slate200.withValues(alpha: 0.5),
                              blurRadius: 20,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Column(
                          children: [
                            // Header
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(20),
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [
                                    AppTheme.primaryBlue,
                                    Color(0xFF1e40af)
                                  ],
                                ),
                                borderRadius: const BorderRadius.vertical(
                                    top: Radius.circular(16)),
                              ),
                              child: Column(
                                children: [
                                  const OsfLogo(size: 36),
                                  const SizedBox(height: 12),
                                  const Text(
                                    'RÉCÉPISSÉ OFFICIEL',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 14,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 2,
                                    ),
                                  ),
                                  Text(
                                    'Microfinance Mali • Conforme BCEAO/UEMOA',
                                    style: TextStyle(
                                      color:
                                          Colors.white.withValues(alpha: 0.8),
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ),
                            ),

                            // Decision badge
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(vertical: 16),
                              color: _receipt!.decision == 'approved'
                                  ? AppTheme.emeraldLight
                                  : _receipt!.decision == 'adjusted'
                                      ? const Color(0xFFdbeafe)
                                      : AppTheme.roseLight,
                              child: Column(
                                children: [
                                  Icon(
                                    _receipt!.decision == 'approved'
                                        ? Icons.check_circle
                                        : _receipt!.decision == 'adjusted'
                                            ? Icons.tune
                                            : Icons.cancel,
                                    size: 40,
                                    color: _receipt!.decision == 'approved'
                                        ? AppTheme.emerald
                                        : _receipt!.decision == 'adjusted'
                                            ? AppTheme.primaryBlue
                                            : AppTheme.rose,
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    _receipt!.decisionLabel,
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w900,
                                      color: _receipt!.decision == 'approved'
                                          ? AppTheme.emerald
                                          : _receipt!.decision == 'adjusted'
                                              ? AppTheme.primaryBlue
                                              : AppTheme.rose,
                                    ),
                                  ),
                                  Text(
                                    formatFCFA(_receipt!.finalAmount),
                                    style: TextStyle(
                                      fontFamily: 'monospace',
                                      fontSize: 16,
                                      fontWeight: FontWeight.w700,
                                      color: _receipt!.decision == 'approved'
                                          ? AppTheme.emerald
                                          : AppTheme.primaryBlue,
                                    ),
                                  ),
                                ],
                              ),
                            ),

                            // Details
                            Padding(
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                children: [
                                  _receiptRow('Référence', _receipt!.reference,
                                      monospace: true),
                                  _divider(),
                                  _receiptRow(
                                      'Client', _receipt!.applicantName),
                                  _divider(),
                                  _receiptRow(
                                      'Email', _receipt!.applicantEmail),
                                  if (_receipt!.applicantPhone != null) ...[
                                    _divider(),
                                    _receiptRow(
                                        'Téléphone', _receipt!.applicantPhone!),
                                  ],
                                  _divider(),
                                  _receiptRow(
                                      'Secteur', _receipt!.activitySector),
                                  _divider(),
                                  _receiptRow('Montant demandé',
                                      formatFCFA(_receipt!.requestedAmount),
                                      monospace: true),
                                  _divider(),
                                  _receiptRow('Score d\'éligibilité',
                                      '${_receipt!.score} / 100',
                                      monospace: true,
                                      color: AppTheme.primaryBlue),
                                  if (_receipt!.accountNumber != null) ...[
                                    _divider(),
                                    _receiptRow('N° Compte IMF',
                                        _receipt!.accountNumber!,
                                        monospace: true,
                                        color: AppTheme.primaryBlue),
                                  ],
                                  _divider(),
                                  _receiptRow(
                                      'Niveau de risque', _receipt!.riskLabel),
                                  if (_receipt!.agentName != null) ...[
                                    _divider(),
                                    _receiptRow(
                                        'Agent traitant', _receipt!.agentName!),
                                  ],
                                  _divider(),
                                  _receiptRow('Date d\'évaluation',
                                      formatDate(_receipt!.scoredAt)),
                                ],
                              ),
                            ),

                            // Footer
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: AppTheme.slate50,
                                borderRadius: const BorderRadius.vertical(
                                    bottom: Radius.circular(16)),
                              ),
                              child: Column(
                                children: [
                                  // QR-like ref box
                                  GestureDetector(
                                    onTap: () {
                                      Clipboard.setData(ClipboardData(
                                          text: _receipt!.receiptId));
                                      ScaffoldMessenger.of(context)
                                          .showSnackBar(
                                        const SnackBar(
                                            content: Text('ID copié !')),
                                      );
                                    },
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 16, vertical: 10),
                                      decoration: BoxDecoration(
                                        color: Colors.white,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                            color: AppTheme.slate200),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(Icons.qr_code,
                                              size: 16,
                                              color: AppTheme.slate500),
                                          const SizedBox(width: 8),
                                          Text(
                                            _receipt!.receiptId,
                                            style: TextStyle(
                                              fontFamily: 'monospace',
                                              fontSize: 11,
                                              color: AppTheme.slate700,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          Icon(Icons.copy,
                                              size: 12,
                                              color: AppTheme.slate400),
                                        ],
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Document officiel non modifiable • Valide sur présentation',
                                    style: TextStyle(
                                      color: AppTheme.slate400,
                                      fontSize: 10,
                                    ),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      )
                          .animate()
                          .fadeIn()
                          .scale(begin: const Offset(0.97, 0.97)),

                      const SizedBox(height: 20),

                      // Share button
                      Builder(
                        builder: (btnCtx) => PrimaryButton(
                          label: 'Partager ce Récépissé',
                          onPressed: () => _share(btnCtx),
                          icon: Icons.share_outlined,
                          width: double.infinity,
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _receiptRow(String label, String value,
      {bool monospace = false, Color? color}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(color: AppTheme.slate500, fontSize: 12)),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 12,
              fontFamily: monospace ? 'monospace' : null,
              color: color,
            ),
            textAlign: TextAlign.end,
          ),
        ),
      ],
    );
  }

  Widget _divider() => const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Divider(height: 1),
      );
}
