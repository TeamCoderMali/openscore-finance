import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/services/auth_service.dart';
import '../../core/services/theme_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';
import '../../shared/widgets/liquid_glass_nav_bar.dart';
import '../dashboard/dashboard_screen.dart';
import '../applications/applications_screen.dart';
import '../documents/documents_screen.dart';
import '../simulator/simulator_screen.dart';
import '../voice_assistant/voice_assistant_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    DashboardScreen(),
    ApplicationsScreen(),
    DocumentsScreen(),
    SimulatorScreen(),
    VoiceAssistantScreen(),
  ];

  final List<LiquidGlassNavBarItem> _navItems = const [
    LiquidGlassNavBarItem(
      icon: Icons.dashboard_outlined,
      activeIcon: Icons.dashboard_rounded,
      label: 'Tableau',
    ),
    LiquidGlassNavBarItem(
      icon: Icons.folder_outlined,
      activeIcon: Icons.folder_rounded,
      label: 'Dossiers',
    ),
    LiquidGlassNavBarItem(
      icon: Icons.description_outlined,
      activeIcon: Icons.description_rounded,
      label: 'Documents',
    ),
    LiquidGlassNavBarItem(
      icon: Icons.calculate_outlined,
      activeIcon: Icons.calculate_rounded,
      label: 'Simulateur',
    ),
    LiquidGlassNavBarItem(
      icon: Icons.mic_none_outlined,
      activeIcon: Icons.mic_rounded,
      label: 'Assistant',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final themeService = context.watch<ThemeService>();
    final user = auth.currentUser;
    final isDark = themeService.isDark;

    return Scaffold(
      extendBody: true,
      appBar: AppBar(
        leading: const Padding(
          padding: EdgeInsets.only(left: 14),
          child: OsfLogo(size: 32, showText: false),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'OpenScore Finance',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w800,
                color: isDark ? Colors.white : AppTheme.slate900,
              ),
            ),
            if (user != null)
              Text(
                user.fullName,
                style: TextStyle(
                  fontSize: 11,
                  color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                  fontWeight: FontWeight.w500,
                ),
              ),
          ],
        ),
        actions: [
          // Reactive Theme toggle
          IconButton(
            icon: Icon(
              isDark ? Icons.light_mode_rounded : Icons.dark_mode_outlined,
              size: 21,
              color: isDark ? AppTheme.amber : AppTheme.primaryBlue,
            ),
            onPressed: () => context.read<ThemeService>().toggleTheme(),
            tooltip: isDark ? 'Passer en mode clair' : 'Passer en mode sombre',
          ),
          // User avatar (elevated, sans dégradé)
          if (user != null)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: GestureDetector(
                onTap: _showUserMenu,
                child: Container(
                  width: 36,
                  height: 36,
                  margin: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue,
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryBlue.withValues(alpha: 0.35),
                        blurRadius: 8,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Center(
                    child: Text(
                      user.initials,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(
            height: 1,
            color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
          ),
        ),
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: LiquidGlassNavBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        items: _navItems,
      ),
    );
  }

  void _showUserMenu() {
    final auth = context.read<AuthService>();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? AppTheme.darkSurface : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkBorder : AppTheme.slate300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 20),
            // User info
            Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue,
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryBlue.withValues(alpha: 0.35),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Center(
                    child: Text(
                      auth.currentUser?.initials ?? 'U',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        auth.currentUser?.fullName ?? '',
                        style: const TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 16),
                      ),
                      Text(
                        auth.currentUser?.email ?? '',
                        style:
                            TextStyle(color: AppTheme.slate500, fontSize: 13),
                      ),
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.emeraldLight,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          'Client Emprunteur',
                          style: TextStyle(
                            color: AppTheme.emerald,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 8),
            ListTile(
              leading: Icon(Icons.logout, color: AppTheme.rose),
              title: Text(
                'Se déconnecter',
                style: TextStyle(
                    color: AppTheme.rose, fontWeight: FontWeight.w600),
              ),
              onTap: () async {
                Navigator.pop(ctx);
                await auth.logout();
                if (mounted) context.go('/welcome');
              },
            ),
          ],
        ),
      ),
    );
  }
}
