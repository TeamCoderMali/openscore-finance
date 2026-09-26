import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../features/splash/splash_screen.dart';
import '../../features/onboarding/onboarding_screen.dart';
import '../../features/welcome/welcome_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/home/home_screen.dart';
import '../../features/applications/application_detail_screen.dart';
import '../../features/documents/receipt_detail_screen.dart';
import '../../features/simulator/simulator_screen.dart';
import '../../features/voice_assistant/voice_assistant_screen.dart';
import '../services/auth_service.dart';

final appRouter = GoRouter(
  initialLocation: '/splash',
  redirect: (context, state) async {
    final auth = context.read<AuthService>();
    final isAuth = auth.isAuthenticated;
    final loc = state.matchedLocation;
    final isPublicRoute = loc == '/splash' ||
        loc == '/onboarding' ||
        loc == '/welcome' ||
        loc == '/login' ||
        loc == '/register' ||
        loc == '/simulator' ||
        loc == '/assistant';

    if (!isAuth && !isPublicRoute) return '/welcome';
    if (isAuth && (loc == '/login' || loc == '/register')) return '/home';
    return null;
  },
  routes: [
    GoRoute(
      path: '/splash',
      pageBuilder: (context, state) => _buildPage(const SplashScreen(), state),
    ),
    GoRoute(
      path: '/onboarding',
      pageBuilder: (context, state) => _buildPage(const OnboardingScreen(), state),
    ),
    GoRoute(
      path: '/welcome',
      pageBuilder: (context, state) => _buildPage(const WelcomeScreen(), state),
    ),
    GoRoute(
      path: '/login',
      pageBuilder: (context, state) => _buildPage(const LoginScreen(), state),
    ),
    GoRoute(
      path: '/register',
      pageBuilder: (context, state) => _buildPage(const RegisterScreen(), state),
    ),
    GoRoute(
      path: '/home',
      pageBuilder: (context, state) => _buildPage(const HomeScreen(), state),
    ),
    GoRoute(
      path: '/application/:id',
      pageBuilder: (context, state) {
        final id = int.parse(state.pathParameters['id']!);
        final ref = state.uri.queryParameters['ref'] ?? '';
        return _buildPage(
          ApplicationDetailScreen(applicationId: id, reference: ref),
          state,
        );
      },
    ),
    GoRoute(
      path: '/receipt/:id',
      pageBuilder: (context, state) {
        final id = int.parse(state.pathParameters['id']!);
        return _buildPage(ReceiptDetailScreen(applicationId: id), state);
      },
    ),
    GoRoute(
      path: '/simulator',
      pageBuilder: (context, state) => _buildPage(
        const Scaffold(body: SafeArea(child: SimulatorScreen())),
        state,
      ),
    ),
    GoRoute(
      path: '/assistant',
      pageBuilder: (context, state) => _buildPage(
        Scaffold(
          appBar: AppBar(
            title: const Text('Assistant Vocal IA', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          ),
          body: const VoiceAssistantScreen(),
        ),
        state,
      ),
    ),
  ],
);

CustomTransitionPage _buildPage(Widget child, GoRouterState state) {
  return CustomTransitionPage(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 250),
    transitionsBuilder: (ctx, animation, secondaryAnimation, child) {
      return FadeTransition(opacity: animation, child: child);
    },
  );
}
