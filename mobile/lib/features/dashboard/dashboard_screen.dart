import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/application_model.dart';
import '../../shared/widgets/shared_widgets.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _api = ApiService();
  List<Application> _applications = [];
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
      final apps = (data['applications'] as List)
          .map((e) => Application.fromJson(e))
          .toList();
      if (mounted) setState(() => _applications = apps);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Application? get _activeApp {
    try {
      return _applications.firstWhere(
        (a) => a.status == 'approved' || a.status == 'adjusted',
      );
    } catch (_) {
      return _applications.isNotEmpty ? _applications.first : null;
    }
  }

  double get _totalActive {
    return _applications
        .where((a) => a.status == 'approved' || a.status == 'adjusted')
        .fold(0, (sum, a) => sum + a.requestedAmount);
  }

  int get _pendingCount =>
      _applications.where((a) => a.status == 'pending_verification').length;
  int get _approvedCount =>
      _applications.where((a) => a.status == 'approved').length;

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().currentUser;
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.primaryBlue,
      child: CustomScrollView(
        slivers: [
          // ── Welcome Banner (Elevated & Sans Dégradé) ───────
          SliverToBoxAdapter(
            child: Container(
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.18),
                  width: 1.2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primaryBlue
                        .withValues(alpha: isDark ? 0.45 : 0.35),
                    blurRadius: 22,
                    offset: const Offset(0, 8),
                  ),
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.08),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Bonjour,',
                          style: TextStyle(
                            inherit: true,
                            color: Colors.white.withValues(alpha: 0.85),
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        Text(
                          user?.fullName.split(' ').first ?? 'Emprunteur',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.4,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.25),
                              width: 0.8,
                            ),
                          ),
                          child: Text(
                            'Microfinance Mali • UEMOA/WA+',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.95),
                              fontSize: 10.5,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 60,
                    height: 60,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.15),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Icon(
                        Icons.account_balance_outlined,
                        color: AppTheme.primaryBlue,
                        size: 30,
                      ),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 400.ms).slideY(begin: -0.1),
          ),

          // ── KPI Grid ───────────────────────────────────────
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            sliver: SliverGrid(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 1.38,
              ),
              delegate: SliverChildListDelegate([
                KpiCard(
                  label: 'ENCOURS TOTAL',
                  value: _loading ? '...' : formatFCFA(_totalActive),
                  subtitle: 'Dossiers actifs en règle',
                  icon: Icons.account_balance_wallet_outlined,
                  iconColor: AppTheme.primaryBlue,
                  valueColor: AppTheme.primaryBlue,
                ).animate().fadeIn(delay: 100.ms),
                KpiCard(
                  label: 'PROCHAINE ÉCHÉANCE',
                  value: '15/10',
                  subtitle: 'Dans 10 jours',
                  icon: Icons.schedule_outlined,
                  iconColor: AppTheme.amber,
                ).animate().fadeIn(delay: 150.ms),
                KpiCard(
                  label: 'DOSSIERS EN ATTENTE',
                  value: _loading ? '...' : '$_pendingCount',
                  subtitle: 'En cours de traitement',
                  icon: Icons.pending_outlined,
                  iconColor: AppTheme.amber,
                  valueColor: _pendingCount > 0 ? AppTheme.amber : null,
                ).animate().fadeIn(delay: 200.ms),
                KpiCard(
                  label: 'DOSSIERS APPROUVÉS',
                  value: _loading ? '...' : '$_approvedCount',
                  subtitle: 'Validés par l\'agent',
                  icon: Icons.check_circle_outline,
                  iconColor: AppTheme.emerald,
                  valueColor: _approvedCount > 0 ? AppTheme.emerald : null,
                ).animate().fadeIn(delay: 250.ms),
              ]),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 20)),

          // ── Repayment Schedule ─────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                children: [
                  SectionTitle(
                    title: 'Échéancier Actif',
                    trailing: TextButton(
                      onPressed: () {},
                      child: Text(
                        'Voir tout',
                        style: TextStyle(
                            color: AppTheme.primaryBlue, fontSize: 12),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _buildSchedule(isDark),
                ],
              ),
            ).animate().fadeIn(delay: 350.ms),
          ),

          // ── Active application info ─────────────────────────
          if (_activeApp != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SectionTitle(title: 'Dossier Actif'),
                    const SizedBox(height: 12),
                    OSFCard(
                      child: Row(
                        children: [
                          ElevatedIconBox(
                            icon: _activeApp!.sectorIcon,
                            iconColor: _activeApp!.sectorColor,
                            size: 44,
                            iconSize: 22,
                            borderRadius: 10,
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _activeApp!.reference,
                                  style: const TextStyle(
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.w700,
                                    fontSize: 13,
                                  ),
                                ),
                                Text(
                                  '${_activeApp!.activitySector} • ${formatFCFA(_activeApp!.requestedAmount)}',
                                  style: TextStyle(
                                      color: AppTheme.slate500, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          StatusBadge(
                            label: _activeApp!.statusLabel,
                            color: _activeApp!.statusColor,
                            bgColor: _activeApp!.statusBg,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ).animate().fadeIn(delay: 400.ms),
            ),

          // ── Stats ──────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  SectionTitle(title: 'Activité récente'),
                  const SizedBox(height: 12),
                  OSFCard(
                    child: Column(
                      children: [
                        _buildStatRow(
                          'Cote de ponctualité',
                          '98.5%',
                          Icons.shield_outlined,
                          AppTheme.emerald,
                          '• Profil Excellent',
                        ),
                        const Divider(height: 20),
                        _buildStatRow(
                          'Total demandes',
                          '${_applications.length}',
                          Icons.folder_outlined,
                          AppTheme.primaryBlue,
                          '• Tous secteurs',
                        ),
                        const Divider(height: 20),
                        _buildStatRow(
                          'Groupement Tontine',
                          'Benkadi GM',
                          Icons.groups_outlined,
                          AppTheme.purple,
                          '• Caution solidaire',
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 450.ms),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 100)),
        ],
      ),
    );
  }

  Widget _buildSchedule(bool isDark) {
    final items = [
      _ScheduleItem(1, '137 500 FCFA', '15/08/2026', 'paid', 'Réglé • Q-0194'),
      _ScheduleItem(2, '137 500 FCFA', '15/09/2026', 'next', 'Prochaine Échéance'),
      _ScheduleItem(3, '137 500 FCFA', '15/10/2026', 'upcoming', 'À venir'),
    ];

    return OSFCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: items.map((item) {
          Color dotColor;
          Color bgColor;
          Color borderColor;
          if (item.status == 'paid') {
            dotColor = AppTheme.emerald;
            bgColor = isDark
                ? AppTheme.emerald.withValues(alpha: 0.15)
                : AppTheme.emeraldLight;
            borderColor = AppTheme.emerald.withValues(alpha: 0.4);
          } else if (item.status == 'next') {
            dotColor = AppTheme.primaryBlue;
            bgColor = isDark
                ? AppTheme.primaryBlue.withValues(alpha: 0.15)
                : const Color(0xFFdbeafe);
            borderColor = AppTheme.primaryBlue.withValues(alpha: 0.4);
          } else {
            dotColor = AppTheme.slate400;
            bgColor = isDark ? AppTheme.darkCard : AppTheme.slate50;
            borderColor = AppTheme.slate200;
          }

          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: borderColor),
            ),
            child: Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: dotColor,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Center(
                    child: item.status == 'paid'
                        ? const Icon(Icons.check, color: Colors.white, size: 14)
                        : Text(
                            '${item.month}',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.w700),
                          ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.amount,
                        style: const TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w700,
                            fontSize: 13),
                      ),
                      Text(
                        item.date,
                        style: TextStyle(
                            color: AppTheme.slate500, fontSize: 11),
                      ),
                    ],
                  ),
                ),
                StatusBadge(
                  label: item.badge,
                  color: dotColor,
                  bgColor: dotColor.withValues(alpha: 0.15),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildStatRow(
      String label, String value, IconData icon, Color color, String sub) {
    return Row(
      children: [
        ElevatedIconBox(
          icon: icon,
          iconColor: color,
          size: 38,
          iconSize: 18,
          borderRadius: 10,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: TextStyle(color: AppTheme.slate500, fontSize: 12)),
              Text(sub, style: TextStyle(color: AppTheme.slate400, fontSize: 10)),
            ],
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 15,
            color: color,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}

class _ScheduleItem {
  final int month;
  final String amount;
  final String date;
  final String status;
  final String badge;

  const _ScheduleItem(this.month, this.amount, this.date, this.status, this.badge);
}
