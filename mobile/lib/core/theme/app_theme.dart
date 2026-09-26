import 'package:flutter/material.dart';

class AppTheme {
  // ── Color Palette (aligned with web frontend) ─────────────────────
  static const Color primaryBlue = Color(0xFF1d4ed8);
  static const Color primaryBlueDark = Color(0xFF1e40af);
  static const Color navy = Color(0xFF0f172a);
  static const Color canvas = Color(0xFFF8FAFC);
  static const Color emerald = Color(0xFF059669);
  static const Color emeraldLight = Color(0xFFd1fae5);
  static const Color rose = Color(0xFFbe123c);
  static const Color roseLight = Color(0xFFffe4e6);
  static const Color amber = Color(0xFFd97706);
  static const Color amberLight = Color(0xFFfef3c7);
  static const Color purple = Color(0xFF7c3aed);
  static const Color purpleLight = Color(0xFFede9fe);

  static const Color slate50 = Color(0xFFF8FAFC);
  static const Color slate100 = Color(0xFFF1F5F9);
  static const Color slate200 = Color(0xFFE2E8F0);
  static const Color slate300 = Color(0xFFCBD5E1);
  static const Color slate400 = Color(0xFF94A3B8);
  static const Color slate500 = Color(0xFF64748B);
  static const Color slate600 = Color(0xFF475569);
  static const Color slate700 = Color(0xFF334155);
  static const Color slate800 = Color(0xFF1E293B);
  static const Color slate900 = Color(0xFF0F172A);

  // Dark mode background layers
  static const Color darkBg = Color(0xFF0b0f19);
  static const Color darkSurface = Color(0xFF111827);
  static const Color darkCard = Color(0xFF1e293b);
  static const Color darkBorder = Color(0xFF334155);

  // ── Symmetrical TextTheme with inherit: true for smooth lerp ───────
  static TextTheme _buildTextTheme({
    required Color primary,
    required Color secondary,
  }) {
    return TextTheme(
      displayLarge: TextStyle(inherit: true, fontWeight: FontWeight.w800, color: primary),
      displayMedium: TextStyle(inherit: true, fontWeight: FontWeight.w700, color: primary),
      displaySmall: TextStyle(inherit: true, fontWeight: FontWeight.w600, color: primary),
      headlineLarge: TextStyle(inherit: true, fontWeight: FontWeight.w700, color: primary),
      headlineMedium: TextStyle(inherit: true, fontWeight: FontWeight.w700, color: primary),
      headlineSmall: TextStyle(inherit: true, fontWeight: FontWeight.w600, color: primary),
      titleLarge: TextStyle(inherit: true, fontWeight: FontWeight.w600, color: primary),
      titleMedium: TextStyle(inherit: true, fontWeight: FontWeight.w600, color: primary),
      titleSmall: TextStyle(inherit: true, fontWeight: FontWeight.w500, color: secondary),
      bodyLarge: TextStyle(inherit: true, color: primary),
      bodyMedium: TextStyle(inherit: true, color: secondary),
      bodySmall: TextStyle(inherit: true, color: secondary, fontSize: 12),
      labelLarge: TextStyle(inherit: true, fontWeight: FontWeight.w600, color: primary, fontSize: 14),
      labelMedium: TextStyle(inherit: true, fontWeight: FontWeight.w500, color: secondary, fontSize: 12),
      labelSmall: TextStyle(inherit: true, fontWeight: FontWeight.w500, color: secondary, fontSize: 10),
    );
  }

  // ── Light Theme ────────────────────────────────────────────────────
  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      platform: TargetPlatform.android,
      typography: Typography.material2021(platform: TargetPlatform.android),
    );
    return base.copyWith(
      scaffoldBackgroundColor: canvas,
      colorScheme: const ColorScheme.light(
        primary: primaryBlue,
        onPrimary: Colors.white,
        secondary: emerald,
        onSecondary: Colors.white,
        error: rose,
        surface: Colors.white,
        onSurface: slate900,
      ),
      textTheme: _buildTextTheme(primary: slate900, secondary: slate600),
      appBarTheme: const AppBarTheme(
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: slate900,
        shadowColor: slate200,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          inherit: true,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: slate900,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shadowColor: const Color(0x140F172A),
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
        ),
        clipBehavior: Clip.antiAlias,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: slate300, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: slate200, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryBlue, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: rose, width: 1),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        hintStyle: const TextStyle(inherit: true, color: slate400, fontSize: 14),
        labelStyle: const TextStyle(inherit: true, color: slate600, fontSize: 13, fontWeight: FontWeight.w600),
        prefixIconColor: slate400,
        suffixIconColor: slate400,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryBlue,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            inherit: true,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: slate700,
          side: const BorderSide(color: slate300),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            inherit: true,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryBlue,
          textStyle: const TextStyle(
            inherit: true,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: primaryBlue,
        unselectedItemColor: slate400,
        elevation: 0,
        selectedLabelStyle: TextStyle(inherit: true, fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(inherit: true, fontSize: 11, fontWeight: FontWeight.w500),
        type: BottomNavigationBarType.fixed,
      ),
      dividerColor: slate200,
    );
  }

  // ── Dark Theme ─────────────────────────────────────────────────────
  static ThemeData dark() {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      platform: TargetPlatform.android,
      typography: Typography.material2021(platform: TargetPlatform.android),
    );
    return base.copyWith(
      scaffoldBackgroundColor: darkBg,
      colorScheme: const ColorScheme.dark(
        primary: Color(0xFF3b82f6),
        onPrimary: Colors.white,
        secondary: Color(0xFF34d399),
        onSecondary: Colors.white,
        error: Color(0xFFf87171),
        surface: darkSurface,
        onSurface: Color(0xFFF1F5F9),
      ),
      textTheme: _buildTextTheme(primary: const Color(0xFFF1F5F9), secondary: const Color(0xFF94A3B8)),
      appBarTheme: const AppBarTheme(
        elevation: 0,
        backgroundColor: darkSurface,
        foregroundColor: Color(0xFFF1F5F9),
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          inherit: true,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: Color(0xFFF1F5F9),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 4,
        shadowColor: Colors.black54,
        color: darkCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: darkBorder, width: 1),
        ),
        clipBehavior: Clip.antiAlias,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF1E293B),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: darkBorder, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: darkBorder, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF60A5FA), width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        hintStyle: const TextStyle(inherit: true, color: Color(0xFF64748B), fontSize: 14),
        labelStyle: const TextStyle(inherit: true, color: Color(0xFF94A3B8), fontSize: 13, fontWeight: FontWeight.w600),
        prefixIconColor: const Color(0xFF64748B),
        suffixIconColor: const Color(0xFF64748B),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF3B82F6),
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            inherit: true,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: const Color(0xFFCBD5E1),
          side: const BorderSide(color: darkBorder),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            inherit: true,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: const Color(0xFF60A5FA),
          textStyle: const TextStyle(
            inherit: true,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: darkSurface,
        selectedItemColor: Color(0xFF60a5fa),
        unselectedItemColor: Color(0xFF64748B),
        elevation: 0,
        selectedLabelStyle: TextStyle(inherit: true, fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(inherit: true, fontSize: 11, fontWeight: FontWeight.w500),
        type: BottomNavigationBarType.fixed,
      ),
      dividerColor: darkBorder,
    );
  }
}
