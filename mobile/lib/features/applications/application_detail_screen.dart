import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/application_model.dart';
import '../../shared/widgets/shared_widgets.dart';

class ApplicationDetailScreen extends StatefulWidget {
  final int applicationId;
  final String reference;

  const ApplicationDetailScreen({
    super.key,
    required this.applicationId,
    required this.reference,
  });

  @override
  State<ApplicationDetailScreen> createState() =>
      _ApplicationDetailScreenState();
}

class _ApplicationDetailScreenState extends State<ApplicationDetailScreen> {
  final _api = ApiService();
  bool _loading = true;
  Application? _app;
  List<AuditLog> _logs = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final [appData, logData] = await Future.wait([
        _api.get('/applications/${widget.applicationId}'),
        _api.get('/applications/${widget.applicationId}/audit-logs'),
      ]);
      _app = Application.fromJson(appData.data);
      _logs = ((logData.data['logs'] as List?) ?? [])
          .map((e) => AuditLog.fromJson(e))
          .toList();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.reference,
          style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _app == null
              ? const EmptyState(
                  message: 'Dossier introuvable',
                  icon: Icons.folder_off_outlined)
              : CustomScrollView(
                  slivers: [
                    // Status header
                    SliverToBoxAdapter(
                      child: Container(
                        margin: const EdgeInsets.all(16),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: _app!.statusBg,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                              color: _app!.statusColor.withValues(alpha: 0.3)),
                        ),
                        child: Row(
                          children: [
                            ElevatedIconBox(
                              icon: _app!.sectorIcon,
                              iconColor: _app!.sectorColor,
                              size: 52,
                              iconSize: 28,
                              borderRadius: 14,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _app!.statusLabel,
                                    style: TextStyle(
                                      color: _app!.statusColor,
                                      fontWeight: FontWeight.w800,
                                      fontSize: 16,
                                    ),
                                  ),
                                  Text(
                                    _app!.activitySectorLabel,
                                    style: TextStyle(
                                        color: AppTheme.slate500, fontSize: 13),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ).animate().fadeIn(),
                    ),

                    // Details grid
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: OSFCard(
                          child: Column(
                            children: [
                              _row('Référence', _app!.reference,
                                  monospace: true),
                              const Divider(height: 20),
                              _row('Montant demandé',
                                  formatFCFA(_app!.requestedAmount)),
                              if (_app!.approvedAmount != null) ...[
                                const Divider(height: 20),
                                _row(
                                  _app!.isAdjusted ? 'Montant accordé (Ajusté)' : 'Montant accordé',
                                  formatFCFA(_app!.approvedAmount!),
                                  color: AppTheme.emerald,
                                ),
                              ],
                              if (_app!.branchCode != null) ...[
                                const Divider(height: 20),
                                _row('Antenne / Caisse', 'Kafo Jiginew ${_app!.branchCode}'),
                              ],
                              if (_app!.applicationType != null) ...[
                                const Divider(height: 20),
                                _row(
                                  'Catégorie',
                                  _app!.applicationTypeLabel,
                                ),
                              ],
                              const Divider(height: 20),
                              _row('Durée',
                                  '${_app!.requestedDurationMonths} mois'),
                              const Divider(height: 20),
                              _row('Date de dépôt',
                                  formatDate(_app!.createdAt)),
                              if (_app!.businessDescription != null) ...[
                                const Divider(height: 20),
                                _row('Description',
                                    _app!.businessDescription!,
                                    multiline: true),
                              ],
                            ],
                          ),
                        ),
                      ).animate().fadeIn(delay: 100.ms),
                    ),

                    // Audit logs
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
                        child: SectionTitle(title: 'Piste d\'Audit'),
                      ),
                    ),

                    if (_logs.isEmpty)
                      const SliverToBoxAdapter(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: EmptyState(
                            message: 'Aucune action enregistrée',
                            icon: Icons.history_outlined,
                          ),
                        ),
                      )
                    else
                      SliverPadding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        sliver: SliverList(
                          delegate: SliverChildBuilderDelegate(
                            (ctx, i) => _AuditLogTile(
                              log: _logs[i],
                              isFirst: i == 0,
                              isLast: i == _logs.length - 1,
                            ),
                            childCount: _logs.length,
                          ),
                        ),
                      ),

                    const SliverToBoxAdapter(child: SizedBox(height: 24)),
                  ],
                ),
    );
  }

  Widget _row(String label, String value,
      {Color? color, bool monospace = false, bool multiline = false}) {
    return Row(
      crossAxisAlignment:
          multiline ? CrossAxisAlignment.start : CrossAxisAlignment.center,
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: AppTheme.slate500, fontSize: 13)),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 13,
              fontFamily: monospace ? 'monospace' : null,
              color: color,
            ),
            textAlign: TextAlign.end,
          ),
        ),
      ],
    );
  }
}

class _AuditLogTile extends StatelessWidget {
  final AuditLog log;
  final bool isFirst;
  final bool isLast;

  const _AuditLogTile({
    required this.log,
    required this.isFirst,
    required this.isLast,
  });

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        children: [
          // Timeline line
          SizedBox(
            width: 32,
            child: Column(
              children: [
                Container(
                  width: 1,
                  height: isFirst ? 16 : 0,
                  color: Colors.transparent,
                ),
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.white, width: 2),
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(width: 1, color: AppTheme.slate200),
                  ),
              ],
            ),
          ),
          // Content
          Expanded(
            child: Container(
              margin: const EdgeInsets.only(left: 8, bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).brightness == Brightness.dark
                    ? AppTheme.darkCard
                    : AppTheme.slate50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.slate200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    log.actionLabel,
                    style: TextStyle(
                      color: AppTheme.primaryBlue,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                      letterSpacing: 0.3,
                    ),
                  ),
                  if (log.userName != null)
                    Text(
                      'Par : ${log.userName}',
                      style: TextStyle(
                          color: AppTheme.slate600, fontSize: 12),
                    ),
                  Text(
                    formatDateTime(log.timestamp),
                    style: TextStyle(
                        color: AppTheme.slate400,
                        fontSize: 10,
                        fontFamily: 'monospace'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
