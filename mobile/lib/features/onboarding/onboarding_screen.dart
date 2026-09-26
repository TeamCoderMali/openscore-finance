import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<_OnboardingPageData> _pages = const [
    _OnboardingPageData(
      badge: 'NORMES BCEAO / UEMOA',
      title: 'Scoring Intelligent\n& Éligibilité Prudentielle',
      subtitle: 'Une analyse de solvabilité juste et instantanée',
      description:
          'Évaluez votre capacité de crédit en moins de 3 minutes grâce à des algorithmes transparents agréés selon les normes prudentielles de la BCEAO.',
      points: [
        'Résultat immédiat basé sur vos flux réels',
        'Explicabilité algorithmique totale (SHAP)',
        'Plafond prudentiel d\'endettement respecté',
      ],
      icon: Icons.account_balance_rounded,
      useBceaoEmblem: true,
    ),
    _OnboardingPageData(
      badge: 'INCLUSION FINANCIÈRE MALI',
      title: 'Assistant Vocal\nFrançais & Bambara',
      subtitle: 'Une microfinance accessible dans votre langue',
      description:
          'Parlez directement dans votre langue : exprimez vos besoins en Bamanankan ou en Français. L\'assistant vous guide pour monter votre dossier pas à pas.',
      points: [
        'Échanges vocaux naturels en Bambara & Français',
        'Adapté aux commerces du Grand Marché et artisans',
        'Crédit Sugu (commerce) & Sɛnɛ (agriculture)',
      ],
      icon: Icons.record_voice_over_rounded,
      useBceaoEmblem: false,
    ),
    _OnboardingPageData(
      badge: 'DÉCAISSEMENT INSTANTANÉ',
      title: 'Déblocage Rapide\n& Suivi en Toute Clarté',
      subtitle: 'Orange Money, Moov Money et virements',
      description:
          'Recevez vos fonds dès validation officielle et suivez l\'état de vos remboursements avec un tableau d\'amortissement clair, sans aucun frais caché.',
      points: [
        'Réception directe sur votre compte Mobile Money',
        'Récépissé officiel horodaté téléchargeable',
        'Rappels d\'échéances par SMS et notifications',
      ],
      icon: Icons.payments_rounded,
      useBceaoEmblem: false,
    ),
  ];

  Future<void> _completeOnboarding() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('has_seen_onboarding', true);
    if (mounted) {
      context.go('/welcome');
    }
  }

  void _nextPage() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeInOutCubic,
      );
    } else {
      _completeOnboarding();
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBg : AppTheme.canvas,
      body: SafeArea(
        child: Column(
          children: [
            // ── Top Bar with Logo & Skip Button ─────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Flexible(
                    child: OsfLogo(size: 38),
                  ),
                  TextButton(
                    onPressed: _completeOnboarding,
                    style: TextButton.styleFrom(
                      foregroundColor: isDark ? AppTheme.slate400 : AppTheme.slate600,
                      textStyle: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    child: const Text('Passer'),
                  ),
                ],
              ),
            ),

            // ── Swipeable PageView ──────────────────────────────────
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                itemCount: _pages.length,
                onPageChanged: (index) {
                  setState(() => _currentPage = index);
                },
                itemBuilder: (context, index) {
                  final data = _pages[index];
                  return _buildPageItem(data, isDark);
                },
              ),
            ),

            // ── Bottom Navigation & Dots Indicator ──────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Smooth Dots Indicator
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(_pages.length, (index) {
                      final isActive = index == _currentPage;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        height: 8,
                        width: isActive ? 26 : 8,
                        decoration: BoxDecoration(
                          color: isActive
                              ? AppTheme.primaryBlue
                              : (isDark ? const Color(0xFF334155) : const Color(0xFFCBD5E1)),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      );
                    }),
                  ),

                  const SizedBox(height: 22),

                  // Main Action Button (Next / Finish)
                  PrimaryButton(
                    label: _currentPage == _pages.length - 1
                        ? 'Accéder à mon Espace'
                        : 'Continuer',
                    icon: _currentPage == _pages.length - 1
                        ? Icons.check_circle_rounded
                        : Icons.arrow_forward_rounded,
                    width: double.infinity,
                    onPressed: _nextPage,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPageItem(_OnboardingPageData data, bool isDark) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const SizedBox(height: 10),

          // Central Hero Illustration / Emblem Box (Solid Blue, NO Gradient)
          Container(
            width: 110,
            height: 110,
            decoration: BoxDecoration(
              color: AppTheme.primaryBlue, // Flat solid royal blue (sans dégradé)
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.32),
                  blurRadius: 18,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            padding: const EdgeInsets.all(16),
            child: data.useBceaoEmblem
                ? const CustomPaint(
                    painter: BceaoMonetaryEmblemPainter(color: Colors.white),
                  )
                : Icon(
                    data.icon,
                    size: 54,
                    color: Colors.white,
                  ),
          ).animate().scale(duration: 400.ms, curve: Curves.easeOutBack),

          const SizedBox(height: 24),

          // Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.primaryBlue.withValues(alpha: isDark ? 0.2 : 0.1),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: AppTheme.primaryBlue.withValues(alpha: isDark ? 0.4 : 0.25),
              ),
            ),
            child: Text(
              data.badge,
              style: const TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.w800,
                color: AppTheme.primaryBlue,
                letterSpacing: 0.5,
              ),
            ),
          ).animate().fadeIn(delay: 150.ms),

          const SizedBox(height: 14),

          // Main Title
          Text(
            data.title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 23,
              fontWeight: FontWeight.w800,
              color: isDark ? Colors.white : AppTheme.slate900,
              height: 1.2,
              letterSpacing: -0.3,
            ),
          ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.08),

          const SizedBox(height: 8),

          // Subtitle
          Text(
            data.subtitle,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
              color: AppTheme.primaryBlue,
            ),
          ).animate().fadeIn(delay: 250.ms),

          const SizedBox(height: 12),

          // Description
          Text(
            data.description,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13,
              color: isDark ? const Color(0xFF94A3B8) : AppTheme.slate600,
              height: 1.45,
            ),
          ).animate().fadeIn(delay: 300.ms),

          const SizedBox(height: 22),

          // 3 Highlights Checkpoints
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B).withValues(alpha: 0.7) : Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: data.points.map((pt) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(3),
                        decoration: BoxDecoration(
                          color: AppTheme.emeraldLight,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.check_rounded,
                          size: 13,
                          color: AppTheme.emerald,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          pt,
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w500,
                            color: isDark ? Colors.white : AppTheme.slate800,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ).animate().fadeIn(delay: 350.ms).slideY(begin: 0.06),
        ],
      ),
    );
  }
}

class _OnboardingPageData {
  final String badge;
  final String title;
  final String subtitle;
  final String description;
  final List<String> points;
  final IconData icon;
  final bool useBceaoEmblem;

  const _OnboardingPageData({
    required this.badge,
    required this.title,
    required this.subtitle,
    required this.description,
    required this.points,
    required this.icon,
    required this.useBceaoEmblem,
  });
}
