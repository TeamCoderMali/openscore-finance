import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/services/auth_service.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/shared_widgets.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController(text: '');
  final _passCtrl = TextEditingController(text: '');
  bool _obscure = true;
  bool _demoFilled = false;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  void _fillDemo() {
    setState(() {
      _emailCtrl.text = 'amadou.diallo@mail.ml';
      _passCtrl.text = 'password123';
      _demoFilled = true;
    });
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final auth = context.read<AuthService>();
    final ok = await auth.login(_emailCtrl.text.trim(), _passCtrl.text.trim());
    if (ok && mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBg : AppTheme.canvas,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            children: [
              // ── Top Bar with Back Button & Theme Toggle ─────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.arrow_back_rounded),
                        tooltip: 'Retour à l\'accueil',
                        onPressed: () {
                          if (context.canPop()) {
                            context.pop();
                          } else {
                            context.go('/welcome');
                          }
                        },
                      ),
                      const SizedBox(width: 4),
                      const OsfLogo(size: 36),
                    ],
                  ),
                  const LiquidGlassThemeToggle(),
                ],
              ).animate().fadeIn(duration: 400.ms),

              const SizedBox(height: 24),

              // ── Hero Liquid Glass Card (Sans Dégradé) ─────────
              LiquidGlassCard(
                borderRadius: 22,
                padding:
                    const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
                child: SizedBox(
                  width: size.width * 0.78,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ElevatedIconBox(
                        icon: Icons.account_balance_outlined,
                        iconColor: AppTheme.primaryBlue,
                        size: 58,
                        iconSize: 28,
                        borderRadius: 16,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Microfinance Mali',
                        style: TextStyle(
                          color: isDark
                              ? const Color(0xFF60A5FA)
                              : AppTheme.primaryBlue,
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                          letterSpacing: 0.2,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'BCEAO • CIF • WA+',
                        style: TextStyle(
                          color: isDark
                              ? const Color(0xFF64748B)
                              : AppTheme.slate400,
                          fontSize: 10.5,
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              )
                  .animate()
                  .fadeIn(delay: 150.ms)
                  .scale(begin: const Offset(0.94, 0.94)),

              const SizedBox(height: 28),

              // ── Title & Subtitle (High contrast) ──────────────
              Text(
                'Connexion à votre espace',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : AppTheme.slate900,
                  letterSpacing: -0.3,
                ),
                textAlign: TextAlign.center,
              ).animate().fadeIn(delay: 250.ms),
              const SizedBox(height: 6),
              Text(
                'Emprunteur • Espace Sécurisé',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: isDark ? const Color(0xFF94A3B8) : AppTheme.slate500,
                ),
              ).animate().fadeIn(delay: 300.ms),

              const SizedBox(height: 24),

              // ── Form ──────────────────────────────────────────
              Form(
                key: _formKey,
                child: Column(
                  children: [
                    // Error banner
                    if (auth.error != null)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: AppTheme.roseLight,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                              color: AppTheme.rose.withValues(alpha: 0.4)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.error_outline,
                                color: AppTheme.rose, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                auth.error!,
                                style: TextStyle(
                                    color: AppTheme.rose,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500),
                              ),
                            ),
                          ],
                        ),
                      ).animate().shakeX(),

                    // Email
                    TextFormField(
                      controller: _emailCtrl,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Adresse Email',
                        hintText: 'votre@email.ml',
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'Email requis';
                        if (!v.contains('@')) return 'Email invalide';
                        return null;
                      },
                    ).animate().fadeIn(delay: 400.ms).slideX(begin: -0.1),

                    const SizedBox(height: 14),

                    // Password
                    TextFormField(
                      controller: _passCtrl,
                      obscureText: _obscure,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: 'Mot de passe',
                        hintText: '••••••••',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          icon: Icon(_obscure
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty)
                          return 'Mot de passe requis';
                        if (v.length < 6) return 'Minimum 6 caractères';
                        return null;
                      },
                    ).animate().fadeIn(delay: 450.ms).slideX(begin: -0.1),

                    const SizedBox(height: 24),

                    // Submit
                    PrimaryButton(
                      label: 'Se Connecter',
                      onPressed: _submit,
                      isLoading: auth.isLoading,
                      icon: Icons.login,
                      width: double.infinity,
                    ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.1),

                    const SizedBox(height: 14),

                    // Demo shortcut
                    OutlinedButton.icon(
                      onPressed: _fillDemo,
                      icon: Icon(
                        Icons.flash_on,
                        size: 16,
                        color: _demoFilled ? AppTheme.emerald : AppTheme.amber,
                      ),
                      label: Text(
                        _demoFilled
                            ? 'Compte démo chargé'
                            : 'Compte démo (Amadou Diallo)',
                        style: TextStyle(
                          inherit: true,
                          color:
                              _demoFilled ? AppTheme.emerald : AppTheme.amber,
                          fontSize: 13,
                        ),
                      ),
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(
                          color: _demoFilled
                              ? AppTheme.emerald.withValues(alpha: 0.5)
                              : AppTheme.amber.withValues(alpha: 0.5),
                        ),
                        textStyle: const TextStyle(
                          inherit: true,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ).animate().fadeIn(delay: 550.ms),
                  ],
                ),
              ),

              const SizedBox(height: 32),
              const Divider(),
              const SizedBox(height: 16),

              // Register link (using Wrap to prevent any overflow on small screens)
              Wrap(
                alignment: WrapAlignment.center,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 4,
                runSpacing: 4,
                children: [
                  Text(
                    'Pas encore de compte ? ',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  GestureDetector(
                    onTap: () {
                      auth.clearError();
                      context.go('/register');
                    },
                    child: const Text(
                      'Créer un compte',
                      style: TextStyle(
                        color: AppTheme.primaryBlue,
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ).animate().fadeIn(delay: 600.ms),

              const SizedBox(height: 12),

              TextButton.icon(
                onPressed: () {
                  auth.clearError();
                  context.go('/welcome');
                },
                icon: const Icon(Icons.arrow_back_rounded, size: 15),
                label: const Text(
                  'Continuer sans compte • Retour au portail',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                style: TextButton.styleFrom(
                  foregroundColor:
                      isDark ? const Color(0xFF94A3B8) : AppTheme.slate600,
                ),
              ),

              const SizedBox(height: 12),

              // UEMOA / BCEAO badge (Flexible to fit any screen width without overflow)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : AppTheme.slate100,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isDark ? AppTheme.darkBorder : AppTheme.slate200,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.lock_outline_rounded,
                      size: 12,
                      color:
                          isDark ? const Color(0xFF94A3B8) : AppTheme.slate500,
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        'Connexion sécurisée • BCEAO / CIF',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          inherit: true,
                          color: isDark
                              ? const Color(0xFF94A3B8)
                              : AppTheme.slate500,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ).animate().fadeIn(delay: 700.ms),
            ],
          ),
        ),
      ),
    );
  }
}
