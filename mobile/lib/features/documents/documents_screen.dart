import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/application_model.dart';
import '../../shared/widgets/shared_widgets.dart';
import 'receipt_detail_screen.dart';

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  final _api = ApiService();
  List<Application> _apps = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _api.getApplications();
      _apps = (data['applications'] as List)
          .map((e) => Application.fromJson(e))
          .toList();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  List<Application> get _approvedApps => _apps
      .where((a) =>
          a.status.toLowerCase() == 'approved' ||
          a.status.toLowerCase() == 'adjusted')
      .toList();

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.primaryBlue,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Récépissés & Documents',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ).animate().fadeIn(),
                  Text(
                    'Documents officiels BCEAO • Consultez et partagez',
                    style: Theme.of(context).textTheme.bodySmall,
                  ).animate().fadeIn(delay: 100.ms),
                  const SizedBox(height: 16),
                  // Info banner
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryBlue.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                          color: AppTheme.primaryBlue.withValues(alpha: 0.2)),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.info_outline,
                            color: AppTheme.primaryBlue, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Les récépissés officiels sont délivrés dès qu\'un dossier est validé et approuvé par le comité de crédit.',
                            style: TextStyle(
                                color: AppTheme.primaryBlue,
                                fontSize: 11),
                          ),
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 150.ms),
                ],
              ),
            ),
          ),

          if (_loading)
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (_, i) => Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 5),
                  child: ShimmerCard(height: 100),
                ),
                childCount: 3,
              ),
            )
          else if (_approvedApps.isEmpty)
            const SliverFillRemaining(
              child: EmptyState(
                message: 'Aucun document disponible pour le moment.\nVos récépissés officiels apparaîtront ici dès que vos dossiers seront approuvés par le comité de crédit.',
                icon: Icons.description_outlined,
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (ctx, i) => _DocCard(app: _approvedApps[i], index: i),
                  childCount: _approvedApps.length,
                ),
              ),
            ),

          const SliverToBoxAdapter(child: SizedBox(height: 100)),
        ],
      ),
    );
  }
}

class _DocCard extends StatelessWidget {
  final Application app;
  final int index;

  const _DocCard({required this.app, required this.index});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: OSFCard(
        child: Row(
          children: [
            // Doc icon (elevated, sans dégradé)
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.1)
                      : const Color(0xFFE2E8F0),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primaryBlue
                        .withValues(alpha: isDark ? 0.25 : 0.12),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.receipt_long_outlined,
                      size: 24, color: AppTheme.primaryBlue),
                  Text('PDF',
                      style: TextStyle(
                          color: isDark ? const Color(0xFF60A5FA) : AppTheme.primaryBlue,
                          fontSize: 9,
                          fontWeight: FontWeight.w800)),
                ],
              ),
            ),
            const SizedBox(width: 14),
            // Info
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
                    '${app.activitySector} • ${formatFCFA(app.requestedAmount)}',
                    style: TextStyle(
                        color: AppTheme.slate500, fontSize: 12),
                  ),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      StatusBadge(
                        label: app.statusLabel,
                        color: app.statusColor,
                        bgColor: app.statusBg,
                      ),
                      Text(
                        formatDate(app.createdAt),
                        style: TextStyle(
                            color: AppTheme.slate400,
                            fontSize: 10,
                            fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            // Action
            IconButton(
              icon: Icon(Icons.arrow_forward_ios,
                  size: 14, color: AppTheme.slate400),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ReceiptDetailScreen(applicationId: app.id),
                ),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: Duration(milliseconds: 80 * index)).slideX(begin: 0.05);
  }
}
