import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';
import '../documents/receipt_detail_screen.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  final _api = ApiService();

  // Account Lookup state for "J'ai un compte"
  final _accountCtrl = TextEditingController(text: 'CMF-2026-001245');
  bool _searchingAccount = false;
  Map<String, dynamic>? _foundAccount;
  String? _accountError;

  // New Quick Request state
  double _requestedAmount = 1000000;
  final int _requestedDuration = 12;
  bool _creatingApp = false;

  @override
  void dispose() {
    _accountCtrl.dispose();
    super.dispose();
  }

  void _showAccountBranchingDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _buildBranchingSheet(ctx),
    );
  }

  Widget _buildBranchingSheet(BuildContext ctx) {
    final isDark = Theme.of(ctx).brightness == Brightness.dark;

    return StatefulBuilder(
      builder: (context, setSheetState) {
        return Container(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 24,
            bottom: MediaQuery.of(context).viewInsets.bottom + 24,
          ),
          decoration: BoxDecoration(
            color: isDark ? AppTheme.darkCard : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppTheme.slate300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Question Header
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.account_balance_rounded, color: AppTheme.primaryBlue, size: 24),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Demande de Microcrédit',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                          ),
                          Text(
                            'Avez-vous déjà un compte microfinance ?',
                            style: TextStyle(fontSize: 12, color: AppTheme.slate500),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // IF NO ACCOUNT CHOSEN YET
                if (_foundAccount == null) ...[
                  // Option 1: OUI - J'ai un compte
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryBlue.withValues(alpha: 0.04),
                      border: Border.all(color: AppTheme.primaryBlue.withValues(alpha: 0.3)),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.check_circle_rounded, color: AppTheme.primaryBlue, size: 20),
                            SizedBox(width: 8),
                            Text(
                              'OUI, j\'ai un compte microfinance',
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: AppTheme.primaryBlue),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Saisissez votre numéro de compte (ex: CMF-2026-001245). Vos informations certifiées seront immédiatement récupérées.',
                          style: TextStyle(fontSize: 11, color: AppTheme.slate600),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _accountCtrl,
                                textCapitalization: TextCapitalization.characters,
                                style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700, fontSize: 13),
                                decoration: InputDecoration(
                                  hintText: 'CMF-2026-XXXXXX',
                                  isDense: true,
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            ElevatedButton(
                              onPressed: _searchingAccount
                                  ? null
                                  : () async {
                                      final acc = _accountCtrl.text.trim();
                                      if (acc.isEmpty) return;
                                      setSheetState(() {
                                        _searchingAccount = true;
                                        _accountError = null;
                                      });
                                      try {
                                        final info = await _api.lookupAccount(acc);
                                        setSheetState(() {
                                          _foundAccount = info;
                                        });
                                      } catch (e) {
                                        setSheetState(() {
                                          _accountError = 'Numéro de compte introuvable. Vérifiez la référence.';
                                        });
                                      } finally {
                                        setSheetState(() => _searchingAccount = false);
                                      }
                                    },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.primaryBlue,
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                              ),
                              child: _searchingAccount
                                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                  : const Text('Valider', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                            ),
                          ],
                        ),
                        if (_accountError != null) ...[
                          const SizedBox(height: 8),
                          Text(_accountError!, style: const TextStyle(color: AppTheme.rose, fontSize: 11, fontWeight: FontWeight.w600)),
                        ],
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Option 2: NON - Je n'ai pas de compte
                  GestureDetector(
                    onTap: () {
                      Navigator.pop(ctx);
                      // Go to simulator with non-member guidance
                      context.push('/simulator');
                    },
                    child: Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: isDark ? AppTheme.darkCard : Colors.white,
                        border: Border.all(color: AppTheme.slate200),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.info_outline_rounded, color: AppTheme.amber, size: 20),
                              const SizedBox(width: 8),
                              const Text(
                                'NON, je n\'ai pas encore de compte',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                              ),
                              const Spacer(),
                              const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppTheme.slate400),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Simulez votre capacité d\'emprunt sur base 100 et découvrez les critères pour ouvrir un compte auprès d\'une microfinance partenaire.',
                            style: TextStyle(fontSize: 11, color: AppTheme.slate500),
                          ),
                        ],
                      ),
                    ),
                  ),
                ] else ...[
                  // ACCOUNT FOUND PREVIEW & PRE-FILLED CONFIRMATION
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.emerald.withValues(alpha: 0.06),
                      border: Border.all(color: AppTheme.emerald.withValues(alpha: 0.4)),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.verified_user_rounded, color: AppTheme.emerald, size: 22),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _foundAccount!['full_name'] ?? 'Client Identifié',
                                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                                  ),
                                  Text(
                                    'Compte IMF : ${_foundAccount!['account_number']}',
                                    style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: AppTheme.emerald, fontWeight: FontWeight.w700),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const Divider(height: 16),
                        Text(
                          'Secteur : ${_foundAccount!['activity_sector']} • Revenus : ${formatFCFA((_foundAccount!['monthly_revenue'] ?? 0).toDouble())}',
                          style: TextStyle(fontSize: 11, color: AppTheme.slate600),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Montant sollicité (FCFA) :',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Expanded(
                              child: Slider(
                                value: _requestedAmount,
                                min: 100000,
                                max: 5000000,
                                divisions: 49,
                                activeColor: AppTheme.primaryBlue,
                                label: formatFCFA(_requestedAmount),
                                onChanged: (v) => setSheetState(() => _requestedAmount = v),
                              ),
                            ),
                            Text(
                              formatFCFA(_requestedAmount),
                              style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w800, fontSize: 12),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _creatingApp
                                ? null
                                : () async {
                                    setSheetState(() => _creatingApp = true);
                                    try {
                                      // Create loan application prefilled with account details
                                      final newApp = await _api.createApplication({
                                        'account_number': _foundAccount!['account_number'],
                                        'activity_sector': _foundAccount!['activity_sector'] ?? 'Commerce',
                                        'requested_amount': _requestedAmount,
                                        'requested_duration_months': _requestedDuration,
                                        'business_description': 'Demande de crédit rattachée au compte ${_foundAccount!['account_number']}',
                                      });
                                      if (context.mounted) {
                                        Navigator.pop(ctx);
                                        context.push('/application/${newApp['id']}?ref=${newApp['reference']}');
                                      }
                                    } catch (e) {
                                      // If user not authenticated, navigate to login or show notice
                                      if (context.mounted) {
                                        Navigator.pop(ctx);
                                        context.push('/login');
                                      }
                                    } finally {
                                      setSheetState(() => _creatingApp = false);
                                    }
                                  },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.emerald,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            child: _creatingApp
                                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                                : const Text('Créer mon Dossier & Continuer', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final auth = context.watch<AuthService>();

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBg : AppTheme.canvas,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Bar
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const OsfLogo(size: 34),
                  if (auth.isAuthenticated)
                    ElevatedButton.icon(
                      onPressed: () => context.go('/home'),
                      icon: const Icon(Icons.dashboard_rounded, size: 16),
                      label: const Text('Mon Espace', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryBlue,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                      ),
                    )
                  else
                    TextButton.icon(
                      onPressed: () => context.push('/login'),
                      icon: const Icon(Icons.login_rounded, size: 16),
                      label: const Text('Connexion', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    ),
                ],
              ),
              const SizedBox(height: 24),

              // Hero Banner
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: AppTheme.primaryBlue,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primaryBlue.withValues(alpha: isDark ? 0.4 : 0.25),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.shield_rounded, size: 12, color: Colors.white),
                          SizedBox(width: 4),
                          Text(
                            'ZONE UEMOA / MALI • CONFORME BCEAO',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.8,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Le microcrédit simplifié,\ntransparent & équitable.',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        height: 1.25,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Évaluez votre solvabilité en quelques minutes et débloquez votre financement auprès de nos IMF partenaires.',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.05, end: 0),

              const SizedBox(height: 28),

              const Text(
                'QUE SOUHAITEZ-VOUS FAIRE ?',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                  color: AppTheme.slate500,
                ),
              ),
              const SizedBox(height: 14),

              // Action 1: Demande de crédit (Branching Dialog)
              _buildActionCard(
                icon: Icons.add_task_rounded,
                iconColor: Colors.white,
                iconBg: AppTheme.primaryBlue,
                title: 'Faire une demande de crédit',
                subtitle: 'Demande avec ou sans compte microfinance préexistant',
                tag: 'Recommandé',
                tagColor: AppTheme.emerald,
                onTap: _showAccountBranchingDialog,
              ).animate().fadeIn(delay: 100.ms),

              const SizedBox(height: 12),

              // Action 2: Simulateur sur base 100
              _buildActionCard(
                icon: Icons.calculate_rounded,
                iconColor: AppTheme.primaryBlue,
                iconBg: AppTheme.primaryBlue.withValues(alpha: 0.1),
                title: 'Simuler ma capacité de crédit',
                subtitle: 'Évaluation gratuite sur base 100 avec garanties & dettes',
                onTap: () => context.push('/simulator'),
              ).animate().fadeIn(delay: 150.ms),

              const SizedBox(height: 12),

              // Action 3: Assistant Vocal Gemini
              _buildActionCard(
                icon: Icons.record_voice_over_rounded,
                iconColor: AppTheme.purple,
                iconBg: AppTheme.purple.withValues(alpha: 0.1),
                title: 'Assistant Vocal & IA Gemini',
                subtitle: 'Échangez vocalement en Français ou en Bambara',
                tag: 'IA Active',
                tagColor: AppTheme.purple,
                onTap: () => context.push('/assistant'),
              ).animate().fadeIn(delay: 200.ms),

              const SizedBox(height: 12),

              // Action 4: Consulter mes dossiers en cours
              _buildActionCard(
                icon: Icons.folder_open_rounded,
                iconColor: AppTheme.slate600,
                iconBg: AppTheme.slate200.withValues(alpha: 0.5),
                title: 'Consulter mes dossiers en cours',
                subtitle: 'Suivi en temps réel de vos demandes et récépissés',
                onTap: () {
                  if (auth.isAuthenticated) {
                    context.go('/home');
                  } else {
                    _showDossierLookupSheet(context);
                  }
                },
              ).animate().fadeIn(delay: 250.ms),

              const SizedBox(height: 32),

              // Educational Footer / Institutions partenaires
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.slate200),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.emerald.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.verified_rounded, color: AppTheme.emerald, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Réseau d\'Institutions Agréées',
                            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12),
                          ),
                          Text(
                            'Vos données sont protégées et vos demandes transmises aux IMF agréées de la zone UEMOA.',
                            style: TextStyle(fontSize: 10, color: AppTheme.slate500, height: 1.3),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionCard({
    required IconData icon,
    required Color iconColor,
    required Color iconBg,
    required String title,
    required String subtitle,
    String? tag,
    Color? tagColor,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.darkCard : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppTheme.slate200.withValues(alpha: isDark ? 0.15 : 0.8)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: iconColor, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          title,
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                        ),
                      ),
                      if (tag != null) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: (tagColor ?? AppTheme.primaryBlue).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            tag,
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              color: tagColor ?? AppTheme.primaryBlue,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: TextStyle(fontSize: 11, color: AppTheme.slate500, height: 1.3),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppTheme.slate400),
          ],
        ),
      ),
    );
  }

  void _showDossierLookupSheet(BuildContext ctx) {
    final isDark = Theme.of(ctx).brightness == Brightness.dark;
    final lookupCtrl = TextEditingController(text: 'CMF-2026-001245');
    bool searching = false;
    Map<String, dynamic>? accountData;
    String? errorMsg;

    showModalBottomSheet(
      context: ctx,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetCtx) => StatefulBuilder(
        builder: (context, setModalState) {
          return Container(
            padding: EdgeInsets.only(
              left: 20,
              right: 20,
              top: 24,
              bottom: MediaQuery.of(context).viewInsets.bottom + 24,
            ),
            decoration: BoxDecoration(
              color: isDark ? AppTheme.darkCard : Colors.white,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Suivi de Dossiers & Récépissés',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.white : AppTheme.slate900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Saisissez votre numéro de compte microfinance pour consulter vos dossiers sans avoir besoin de mot de passe.',
                    style: TextStyle(fontSize: 12, color: AppTheme.slate500, height: 1.35),
                  ),
                  const SizedBox(height: 16),

                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: lookupCtrl,
                          decoration: InputDecoration(
                            labelText: 'Numéro de Compte IMF (ex: CMF-...)',
                            hintText: 'CMF-2026-001245',
                            prefixIcon: const Icon(Icons.credit_card_rounded, size: 18),
                            isDense: true,
                            errorText: errorMsg,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: searching
                            ? null
                            : () async {
                                final term = lookupCtrl.text.trim();
                                if (term.isEmpty) return;
                                setModalState(() {
                                  searching = true;
                                  errorMsg = null;
                                });
                                try {
                                  final data = await _api.lookupAccount(term);
                                  setModalState(() {
                                    accountData = data;
                                    searching = false;
                                  });
                                } catch (e) {
                                  setModalState(() {
                                    errorMsg = 'Compte introuvable ou erreur réseau';
                                    searching = false;
                                  });
                                }
                              },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primaryBlue,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: searching
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Text('Vérifier', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),

                  if (accountData != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryBlue.withValues(alpha: 0.07),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.primaryBlue.withValues(alpha: 0.2)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.account_circle_rounded, color: AppTheme.primaryBlue, size: 24),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  accountData!['full_name'] ?? 'Titulaire',
                                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                                ),
                                Text(
                                  '${accountData!['institution_name'] ?? 'IMF Partenaire'} • ${accountData!['account_number']}',
                                  style: const TextStyle(fontSize: 11, color: AppTheme.slate500),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Dossiers Associés (${(accountData!['past_applications'] as List?)?.length ?? 0})',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppTheme.slate600),
                    ),
                    const SizedBox(height: 8),
                    if ((accountData!['past_applications'] as List?)?.isEmpty ?? true)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          'Aucun dossier de crédit trouvé pour ce compte.',
                          style: TextStyle(fontSize: 12, color: AppTheme.slate400),
                        ),
                      )
                    else
                      ...((accountData!['past_applications'] as List).map((app) {
                        final status = app['status']?.toString() ?? 'draft';
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                            ),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          app['reference'] ?? 'Dossier',
                                          style: const TextStyle(
                                            fontFamily: 'monospace',
                                            fontWeight: FontWeight.w800,
                                            fontSize: 12,
                                          ),
                                        ),
                                        if (app['score'] != null) ...[
                                          const SizedBox(width: 8),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: AppTheme.primaryBlue.withValues(alpha: 0.12),
                                              borderRadius: BorderRadius.circular(6),
                                            ),
                                            child: Text(
                                              '${app['score']}/100',
                                              style: const TextStyle(
                                                fontSize: 10,
                                                fontWeight: FontWeight.w800,
                                                color: AppTheme.primaryBlue,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      formatFCFA((app['requested_amount'] as num?)?.toDouble() ?? 0),
                                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
                                    ),
                                    const SizedBox(height: 4),
                                    StatusBadge(
                                      label: _frenchStatus(status),
                                      color: _frenchStatusColor(status),
                                      bgColor: _frenchStatusBg(status),
                                    ),
                                  ],
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.receipt_long_rounded, color: AppTheme.primaryBlue, size: 20),
                                tooltip: 'Voir Récépissé',
                                onPressed: () {
                                  Navigator.of(sheetCtx).pop();
                                  Navigator.of(ctx).push(
                                    MaterialPageRoute(
                                      builder: (_) => ReceiptDetailScreen(applicationId: app['id'] as int),
                                    ),
                                  );
                                },
                              ),
                            ],
                          ),
                        );
                      })),
                  ],

                  const SizedBox(height: 16),
                  Center(
                    child: TextButton.icon(
                      onPressed: () {
                        Navigator.of(sheetCtx).pop();
                        ctx.push('/login');
                      },
                      icon: const Icon(Icons.lock_open_rounded, size: 14),
                      label: const Text(
                        'Vous possédez déjà un mot de passe ? Se connecter',
                        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  String _frenchStatus(String status) {
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

  Color _frenchStatusColor(String status) {
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

  Color _frenchStatusBg(String status) {
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
}
