import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../core/services/theme_service.dart';
import '../../core/theme/app_theme.dart';

// ── Currency formatter ─────────────────────────────────────────────
NumberFormat? _cachedFcfaFormatter;

NumberFormat get _fcfaFormatter {
  _cachedFcfaFormatter ??= NumberFormat('#,##0', 'fr_FR');
  return _cachedFcfaFormatter!;
}

String formatFCFA(double amount) {
  try {
    return '${_fcfaFormatter.format(amount)} FCFA';
  } catch (_) {
    final str = amount.toStringAsFixed(0);
    final buffer = StringBuffer();
    int count = 0;
    for (int i = str.length - 1; i >= 0; i--) {
      buffer.write(str[i]);
      count++;
      if (count % 3 == 0 && i > 0) {
        buffer.write(' ');
      }
    }
    final formatted = buffer.toString().split('').reversed.join();
    return '$formatted FCFA';
  }
}

String formatDate(DateTime? date) {
  if (date == null) return '—';
  try {
    return DateFormat('dd/MM/yyyy', 'fr_FR').format(date.toLocal());
  } catch (_) {
    try {
      return DateFormat('dd/MM/yyyy').format(date.toLocal());
    } catch (_) {
      final d = date.toLocal();
      final day = d.day.toString().padLeft(2, '0');
      final month = d.month.toString().padLeft(2, '0');
      return '$day/$month/${d.year}';
    }
  }
}

String formatDateTime(DateTime? date) {
  if (date == null) return '—';
  try {
    return DateFormat('dd/MM/yyyy HH:mm', 'fr_FR').format(date.toLocal());
  } catch (_) {
    try {
      return DateFormat('dd/MM/yyyy HH:mm').format(date.toLocal());
    } catch (_) {
      final d = date.toLocal();
      final day = d.day.toString().padLeft(2, '0');
      final month = d.month.toString().padLeft(2, '0');
      final hour = d.hour.toString().padLeft(2, '0');
      final min = d.minute.toString().padLeft(2, '0');
      return '$day/$month/${d.year} $hour:$min';
    }
  }
}

// ── Liquid Glass Card ──────────────────────────────────────────────
class LiquidGlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final double borderRadius;
  final double blur;
  final Color? tintColor;
  final double elevation;
  final Border? border;

  const LiquidGlassCard({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.borderRadius = 18,
    this.blur = 18,
    this.tintColor,
    this.elevation = 4,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final defaultTint = isDark
        ? const Color(0xFF1E293B).withValues(alpha: 0.65)
        : Colors.white.withValues(alpha: 0.72);
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.12)
        : Colors.white.withValues(alpha: 0.75);

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.45)
                : const Color(0x120F172A),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.25)
                : const Color(0x080F172A),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
          child: Material(
            color: tintColor ?? defaultTint,
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(borderRadius),
              child: Container(
                padding: padding ?? const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(borderRadius),
                  border: border ??
                      Border.all(
                        color: borderColor,
                        width: 1.2,
                      ),
                ),
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Elevated Icon Box (Sans Dégradé) ────────────────────────────────
class ElevatedIconBox extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final double size;
  final double iconSize;
  final double borderRadius;

  const ElevatedIconBox({
    super.key,
    required this.icon,
    required this.iconColor,
    this.size = 36,
    this.iconSize = 18,
    this.borderRadius = 10,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.1)
              : const Color(0xFFE2E8F0),
          width: 1,
        ),
        boxShadow: [
          // Soft colored ambient glow
          BoxShadow(
            color: iconColor.withValues(alpha: isDark ? 0.3 : 0.2),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
          // Clean elevation shadow
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.4)
                : const Color(0x0D0F172A),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Center(
        child: Icon(icon, size: iconSize, color: iconColor),
      ),
    );
  }
}

// ── Premium Elevated Card Widget (Sans Dégradé) ────────────────────
class OSFCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? color;
  final VoidCallback? onTap;
  final double borderRadius;

  const OSFCard({
    super.key,
    required this.child,
    this.padding,
    this.color,
    this.onTap,
    this.borderRadius = 16,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardBg = color ?? (isDark ? AppTheme.darkCard : Colors.white);
    final borderColor = isDark ? AppTheme.darkBorder : const Color(0xFFE2E8F0);

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: [
          // Primary soft depth shadow
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.45)
                : const Color(0x0C0F172A),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
          // Secondary subtle contact shadow
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.2)
                : const Color(0x050F172A),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Material(
        color: cardBg,
        borderRadius: BorderRadius.circular(borderRadius),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(borderRadius),
          child: Container(
            padding: padding ?? const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(borderRadius),
              border: Border.all(
                color: borderColor,
                width: 1,
              ),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}

// ── KPI Card (Elevated & Sans Dégradé) ──────────────────────────────
class KpiCard extends StatelessWidget {
  final String label;
  final String value;
  final String? subtitle;
  final IconData icon;
  final Color iconColor;
  final Color? valueColor;

  const KpiCard({
    super.key,
    required this.label,
    required this.value,
    this.subtitle,
    required this.icon,
    required this.iconColor,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return OSFCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  label,
                  style: theme.textTheme.labelSmall?.copyWith(
                    letterSpacing: 0.5,
                    fontWeight: FontWeight.w700,
                    color: isDark ? const Color(0xFF94A3B8) : AppTheme.slate600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              ElevatedIconBox(
                icon: icon,
                iconColor: iconColor,
                size: 30,
                iconSize: 15,
                borderRadius: 8,
              ),
            ],
          ),
          const SizedBox(height: 6),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              value,
              style: theme.textTheme.titleLarge?.copyWith(
                fontFamily: 'monospace',
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: valueColor ?? (isDark ? Colors.white : AppTheme.slate900),
              ),
              maxLines: 1,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 2),
            Text(
              subtitle!,
              style: theme.textTheme.bodySmall?.copyWith(
                fontSize: 10.5,
                color: isDark ? const Color(0xFF64748B) : AppTheme.slate400,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
}

// ── Liquid Glass Theme Toggle Pill ─────────────────────────────────
class LiquidGlassThemeToggle extends StatelessWidget {
  const LiquidGlassThemeToggle({super.key});

  @override
  Widget build(BuildContext context) {
    final themeService = context.watch<ThemeService>();
    final isDark = themeService.isDark;

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.4)
                : const Color(0x120F172A),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Material(
            color: isDark
                ? const Color(0xFF1E293B).withValues(alpha: 0.7)
                : Colors.white.withValues(alpha: 0.75),
            child: InkWell(
              onTap: () => themeService.toggleTheme(),
              borderRadius: BorderRadius.circular(20),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.15)
                        : Colors.white.withValues(alpha: 0.8),
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      isDark ? Icons.light_mode : Icons.dark_mode_outlined,
                      size: 16,
                      color: isDark ? AppTheme.amber : AppTheme.primaryBlue,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      isDark ? 'Clair' : 'Sombre',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: isDark ? Colors.white : AppTheme.slate800,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Status Badge ───────────────────────────────────────────────────
class StatusBadge extends StatelessWidget {
  final String label;
  final Color color;
  final Color bgColor;

  const StatusBadge({
    super.key,
    required this.label,
    required this.color,
    required this.bgColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}

// ── Primary Button ─────────────────────────────────────────────────
class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;
  final double? width;

  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.isLoading = false,
    this.icon,
    this.width,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        child: isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (icon != null) ...[
                    Icon(icon, size: 18),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    label,
                    style: const TextStyle(inherit: true),
                  ),
                ],
              ),
      ),
    );
  }
}

// ── Gradient Header ────────────────────────────────────────────────
class GradientHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;

  const GradientHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppTheme.primaryBlue, Color(0xFF1e40af)],
        ),
      ),
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.8),
                      fontSize: 12,
                    ),
                  ),
              ],
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

// ── Loading Shimmer Skeleton ───────────────────────────────────────
class ShimmerCard extends StatelessWidget {
  final double height;

  const ShimmerCard({super.key, this.height = 80});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.slate100,
        borderRadius: BorderRadius.circular(12),
      ),
    );
  }
}

// ── Section Title ──────────────────────────────────────────────────
class SectionTitle extends StatelessWidget {
  final String title;
  final Widget? trailing;

  const SectionTitle({super.key, required this.title, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
                letterSpacing: 0.2,
              ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

// ── Empty State ────────────────────────────────────────────────────
class EmptyState extends StatelessWidget {
  final String message;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;

  const EmptyState({
    super.key,
    required this.message,
    this.icon = Icons.inbox_outlined,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: AppTheme.slate300),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppTheme.slate400,
                  ),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 20),
              OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

// ── BCEAO Monetary Emblem Painter (Poisson-scie — Symbole officiel BCEAO) ─
class BceaoMonetaryEmblemPainter extends CustomPainter {
  final Color color;

  const BceaoMonetaryEmblemPainter({this.color = Colors.white});

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 48.0;

    final fillPaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final strokePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6 * s
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    // 1. Currency Medallion Circles (Monetary coin border)
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      20.5 * s,
      strokePaint..strokeWidth = 1.0 * s,
    );
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      18.5 * s,
      strokePaint..strokeWidth = 1.4 * s,
    );

    // 2. BCEAO Sawfish Rostrum (La Scie du poisson-scie BCEAO)
    final stem = RRect.fromRectAndRadius(
      Rect.fromLTWH(8 * s, 22.5 * s, 15 * s, 3 * s),
      Radius.circular(1.5 * s),
    );
    canvas.drawRRect(stem, fillPaint);

    // 4 pairs of calibrated saw teeth
    final toothX = [10.0 * s, 13.5 * s, 17.0 * s, 20.5 * s];
    for (final x in toothX) {
      // Top tooth
      final topP = Path()
        ..moveTo(x - 1.2 * s, 22.5 * s)
        ..lineTo(x, 18.2 * s)
        ..lineTo(x + 1.2 * s, 22.5 * s)
        ..close();
      canvas.drawPath(topP, fillPaint);

      // Bottom tooth
      final btmP = Path()
        ..moveTo(x - 1.2 * s, 25.5 * s)
        ..lineTo(x, 29.8 * s)
        ..lineTo(x + 1.2 * s, 25.5 * s)
        ..close();
      canvas.drawPath(btmP, fillPaint);
    }

    // 3. Fish Body (Corps hydrodynamique)
    final body = Path()
      ..moveTo(22 * s, 24 * s)
      ..cubicTo(23 * s, 19.8 * s, 27 * s, 19.2 * s, 32 * s, 21 * s)
      ..lineTo(37 * s, 23.5 * s)
      ..lineTo(37 * s, 24.5 * s)
      ..cubicTo(32 * s, 26.8 * s, 27 * s, 28.2 * s, 22 * s, 24 * s)
      ..close();
    canvas.drawPath(body, fillPaint);

    // 4. Dorsal Fin (Nageoire dorsale supérieure)
    final dorsal = Path()
      ..moveTo(27 * s, 20.2 * s)
      ..lineTo(30.5 * s, 14.5 * s)
      ..lineTo(32.5 * s, 21 * s)
      ..close();
    canvas.drawPath(dorsal, fillPaint);

    // 5. Ventral Fin (Nageoire ventrale inférieure)
    final ventral = Path()
      ..moveTo(27 * s, 27.8 * s)
      ..lineTo(30.5 * s, 33.5 * s)
      ..lineTo(32.5 * s, 27 * s)
      ..close();
    canvas.drawPath(ventral, fillPaint);

    // 6. Caudal Tail Fin (Queue caudale stylisée)
    final tail = Path()
      ..moveTo(36.5 * s, 24 * s)
      ..lineTo(41.5 * s, 17.5 * s)
      ..quadraticBezierTo(39 * s, 24 * s, 41.5 * s, 30.5 * s)
      ..close();
    canvas.drawPath(tail, fillPaint);

    // 7. Eye (Point central)
    final eyePaint = Paint()
      ..color = (color == Colors.white) ? AppTheme.primaryBlue : Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(24.5 * s, 22.8 * s), 1.2 * s, eyePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ── OSF Logo with BCEAO Monetary Emblem (Solid Blue — Sans Dégradé) ─
class OsfLogo extends StatelessWidget {
  final double size;
  final bool showText;

  const OsfLogo({super.key, this.size = 44, this.showText = true});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Solid Blue Emblem Container (NO Gradient)
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: AppTheme.primaryBlue, // Flat solid royal blue (sans dégradé)
            borderRadius: BorderRadius.circular(size * 0.26),
            boxShadow: [
              BoxShadow(
                color: AppTheme.primaryBlue.withValues(alpha: 0.28),
                blurRadius: 8,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          padding: EdgeInsets.all(size * 0.12),
          child: CustomPaint(
            painter: const BceaoMonetaryEmblemPainter(color: Colors.white),
            size: Size(size, size),
          ),
        ),
        if (showText) ...[
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'OpenScore',
                    style: TextStyle(
                      fontSize: size * 0.35,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.primaryBlue,
                      height: 1.1,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      'BCEAO',
                      style: TextStyle(
                        fontSize: size * 0.18,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primaryBlue,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
              Text(
                'Finance',
                style: TextStyle(
                  fontSize: size * 0.27,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.slate500,
                  height: 1.1,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

// ── Custom Amount Input Dialog & Reusable Slider ───────────────────
Future<void> showCustomAmountBottomSheet({
  required BuildContext context,
  required String title,
  required double currentValue,
  required ValueChanged<double> onSubmitted,
  List<double> presets = const [100000, 250000, 500000, 1000000, 2000000, 5000000],
}) async {
  final ctrl = TextEditingController(text: currentValue.toInt().toString());
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) {
      final isDark = Theme.of(ctx).brightness == Brightness.dark;
      return Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: Container(
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            border: Border.all(
              color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
            ),
          ),
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? AppTheme.slate600 : AppTheme.slate300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                title,
                style: const TextStyle(
                  inherit: true,
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Saisissez librement votre montant exact en FCFA (sans limitation)',
                style: TextStyle(
                  inherit: true,
                  fontSize: 12,
                  color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: ctrl,
                autofocus: true,
                keyboardType: TextInputType.number,
                style: TextStyle(
                  inherit: true,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'monospace',
                  color: isDark ? Colors.white : AppTheme.slate900,
                ),
                decoration: const InputDecoration(
                  suffixText: 'FCFA',
                  suffixStyle: TextStyle(
                    inherit: true,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                  prefixIcon: Icon(Icons.edit_note_rounded),
                  hintText: 'Ex: 750000',
                ),
              ),
              const SizedBox(height: 14),
              Text(
                'Suggestions rapides :',
                style: TextStyle(
                  inherit: true,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: presets.map((amt) {
                  return ActionChip(
                    label: Text(
                      formatFCFA(amt),
                      style: const TextStyle(inherit: true, fontSize: 11, fontWeight: FontWeight.w600),
                    ),
                    onPressed: () {
                      ctrl.text = amt.toInt().toString();
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 20),
              PrimaryButton(
                label: 'Appliquer ce montant',
                icon: Icons.check_circle_outline_rounded,
                width: double.infinity,
                onPressed: () {
                  final text = ctrl.text.replaceAll(RegExp(r'[^0-9.]'), '');
                  final parsed = double.tryParse(text);
                  if (parsed != null && parsed > 0) {
                    onSubmitted(parsed);
                  }
                  Navigator.of(ctx).pop();
                },
              ),
            ],
          ),
        ),
      );
    },
  );
}

class EditableAmountSlider extends StatelessWidget {
  final String label;
  final double value;
  final double min;
  final double max;
  final int divisions;
  final ValueChanged<double> onChanged;
  final Color? color;
  final List<double>? presets;

  const EditableAmountSlider({
    super.key,
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.onChanged,
    this.color,
    this.presets,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveColor = color ?? AppTheme.primaryBlue;
    final isCustomOutside = value > max || value < min;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                label.toUpperCase(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  inherit: true,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.slate500,
                  letterSpacing: 0.6,
                ),
              ),
            ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: () => showCustomAmountBottomSheet(
                context: context,
                title: label,
                currentValue: value,
                onSubmitted: onChanged,
                presets: presets ?? const [100000, 250000, 500000, 1000000, 2000000, 5000000],
              ),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: effectiveColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: effectiveColor.withValues(alpha: 0.35),
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      formatFCFA(value),
                      style: TextStyle(
                        inherit: true,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                        color: effectiveColor,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      Icons.edit_rounded,
                      size: 13,
                      color: effectiveColor,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        if (isCustomOutside) ...[
          const SizedBox(height: 4),
          Text(
            value > max
                ? 'Saisie manuelle : montant supérieur à la limite du curseur'
                : 'Saisie manuelle : montant inférieur à la limite du curseur',
            style: const TextStyle(
              inherit: true,
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppTheme.amber,
            ),
          ),
        ],
        const SizedBox(height: 6),
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            activeTrackColor: effectiveColor,
            inactiveTrackColor: AppTheme.slate200,
            thumbColor: effectiveColor,
            overlayColor: effectiveColor.withValues(alpha: 0.15),
            trackHeight: 4,
          ),
          child: Slider(
            value: value.clamp(min, max),
            min: min,
            max: max,
            divisions: divisions,
            onChanged: onChanged,
          ),
        ),
      ],
    );
  }
}

