import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/application_model.dart';
import '../../shared/widgets/shared_widgets.dart';
import 'new_application_wizard.dart';

class ApplicationsScreen extends StatefulWidget {
  const ApplicationsScreen({super.key});

  @override
  State<ApplicationsScreen> createState() => _ApplicationsScreenState();
}

class _ApplicationsScreenState extends State<ApplicationsScreen> {
  final _api = ApiService();
  List<Application> _apps = [];
  bool _loading = true;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _api.getApplications();
      final apps = (data['applications'] as List)
          .map((e) => Application.fromJson(e))
          .toList();
      if (mounted) setState(() => _apps = apps);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  List<Application> get _filtered {
    if (_filter == 'all') return _apps;
    return _apps.where((a) => a.status == _filter).toList();
  }

  void _openNewWizard() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => NewApplicationWizard(onSuccess: _load),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _load,
        color: AppTheme.primaryBlue,
        child: CustomScrollView(
          slivers: [
            // Header
            SliverToBoxAdapter(
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Mes Dossiers de Crédit',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ).animate().fadeIn(),
                    Text(
                      'Espace Emprunteur • Microfinance Mali',
                      style: Theme.of(context).textTheme.bodySmall,
                    ).animate().fadeIn(delay: 100.ms),
                    const SizedBox(height: 16),

                    // Filter chips
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          _chip('all', 'Tous (${_apps.length})', Icons.folder_outlined),
                          _chip('pending_verification', 'En attente', Icons.hourglass_top_rounded),
                          _chip('approved', 'Approuvés', Icons.check_circle_outline_rounded),
                          _chip('rejected', 'Refusés', Icons.cancel_outlined),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                ),
              ),
            ),

            // List
            if (_loading)
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (_, i) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
                    child: ShimmerCard(height: 90),
                  ),
                  childCount: 4,
                ),
              )
            else if (_filtered.isEmpty)
              SliverFillRemaining(
                child: EmptyState(
                  message: _apps.isEmpty
                      ? 'Aucun dossier pour le moment.\nTapez + pour faire votre première demande.'
                      : 'Aucun dossier pour ce filtre.',
                  icon: Icons.folder_open_outlined,
                  actionLabel: _apps.isEmpty ? 'Nouvelle demande' : null,
                  onAction: _apps.isEmpty ? _openNewWizard : null,
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.all(16),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => _AppCard(
                      app: _filtered[i],
                      onTap: () => context.push(
                          '/application/${_filtered[i].id}?ref=${_filtered[i].reference}'),
                      onReceipt: () =>
                          context.push('/receipt/${_filtered[i].id}'),
                      index: i,
                    ),
                    childCount: _filtered.length,
                  ),
                ),
              ),

            const SliverToBoxAdapter(child: SizedBox(height: 140)),
          ],
        ),
      ),
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 98, right: 6),
        child: FloatingActionButton.extended(
          onPressed: _openNewWizard,
          backgroundColor: AppTheme.primaryBlue,
          foregroundColor: Colors.white,
          elevation: 5,
          icon: const Icon(Icons.add_rounded),
          label: const Text('Nouvelle Demande',
              style: TextStyle(inherit: true, fontWeight: FontWeight.w700)),
        ),
      ),
    );
  }

  Widget _chip(String value, String label, [IconData? icon]) {
    final selected = _filter == value;
    return GestureDetector(
      onTap: () => setState(() => _filter = value),
      child: AnimatedContainer(
        duration: 200.ms,
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primaryBlue : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? AppTheme.primaryBlue : AppTheme.slate200,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 13,
                color: selected ? Colors.white : AppTheme.slate500,
              ),
              const SizedBox(width: 5),
            ],
            Text(
              label,
              style: TextStyle(
                color: selected ? Colors.white : AppTheme.slate600,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Application Card ───────────────────────────────────────────────
class _AppCard extends StatelessWidget {
  final Application app;
  final VoidCallback onTap;
  final VoidCallback onReceipt;
  final int index;

  const _AppCard({
    required this.app,
    required this.onTap,
    required this.onReceipt,
    required this.index,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: OSFCard(
        onTap: onTap,
        child: Column(
          children: [
            Row(
              children: [
                ElevatedIconBox(
                  icon: app.sectorIcon,
                  iconColor: app.sectorColor,
                  size: 46,
                  iconSize: 22,
                  borderRadius: 12,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        app.reference,
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                      Text(
                        '${app.activitySector} • ${app.requestedDurationMonths} mois',
                        style: TextStyle(
                          color: AppTheme.slate500,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                StatusBadge(
                  label: app.statusLabel,
                  color: app.statusColor,
                  bgColor: app.statusBg,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        app.approvedAmount != null
                            ? (app.isAdjusted ? 'Accordé (Ajusté)' : 'Montant accordé')
                            : 'Montant demandé',
                        style: TextStyle(
                          color: app.approvedAmount != null ? AppTheme.emerald : AppTheme.slate500,
                          fontSize: 10,
                          fontWeight: app.approvedAmount != null ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                      Text(
                        formatFCFA(app.approvedAmount ?? app.requestedAmount),
                        style: TextStyle(
                          color: app.approvedAmount != null ? AppTheme.emerald : AppTheme.primaryBlue,
                          fontWeight: FontWeight.w800,
                          fontSize: 14,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('Date de dépôt',
                          style: TextStyle(
                              color: AppTheme.slate500, fontSize: 10)),
                      Text(
                        formatDate(app.createdAt),
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 12),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Builder(
              builder: (context) {
                final bool isApproved = app.status.toLowerCase() == 'approved' ||
                    app.status.toLowerCase() == 'adjusted';
                return Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: onTap,
                        icon: const Icon(Icons.history, size: 14),
                        label: const Text('Historique', style: TextStyle(fontSize: 12)),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: isApproved ? onReceipt : null,
                        icon: Icon(
                          isApproved ? Icons.receipt_long : Icons.lock_outline_rounded,
                          size: 14,
                        ),
                        label: Text(
                          isApproved ? 'Récépissé' : 'En attente',
                          style: const TextStyle(fontSize: 12),
                        ),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          backgroundColor: isApproved ? AppTheme.primaryBlue : null,
                          foregroundColor: isApproved ? Colors.white : null,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: Duration(milliseconds: 80 * index)).slideY(begin: 0.08);
  }
}
