import 'package:flutter/material.dart';

/// CogniCompanion Patient App Theme
/// ================================
/// Calm, dignified, senior-accessible visual system.
/// Adheres strictly to Anti-Vibecoding rules:
/// - Warm linen canvas (#FAF8F5) with crisp stone borders (#E8E4DC)
/// - Solid Deep Slate Teal (#184E5A) primary anchor — no gradients
/// - High-contrast readable typography for seniors with mild cognitive impairment
/// - Generous touch targets and restrained 12-14px corner radii
class AppTheme {
  // ── Palette (Harmonized with Caregiver Workspace) ──────────────────────────
  static const Color background       = Color(0xFFFAF8F5);
  static const Color surfaceCard      = Color(0xFFFFFFFF);
  static const Color primaryTeal      = Color(0xFF184E5A);
  static const Color primaryTealDark  = Color(0xFF123C46);
  static const Color primaryTealLight = Color(0xFFEBF3F4);
  static const Color borderStone      = Color(0xFFE8E4DC);
  static const Color borderSubtle     = borderStone;
  static const Color warmSurface      = Color(0xFFF7F5F0);

  // Text
  static const Color textPrimary   = Color(0xFF1C1917); // Stone-900
  static const Color textSecondary = Color(0xFF78716C); // Stone-500
  static const Color textLight     = Color(0xFFA8A29E); // Stone-400

  // Semantic Accents
  static const Color warmAmber     = Color(0xFFB45309); // Amber / Terracotta
  static const Color amberAccent   = warmAmber;
  static const Color tealSurface   = primaryTealLight;
  static const Color gentleGreen   = Color(0xFF15803D); // Verified Emerald
  static const Color gentleRose    = Color(0xFFB91C1C); // Emergency Red
  static const Color softOrange    = Color(0xFFD97706);
  static const Color softPurple    = Color(0xFF475569); // Slate alternative
  static const Color softBlue      = Color(0xFF184E5A);

  // Legacy aliases
  static const Color softBackground = background;
  static const Color textSub        = textSecondary;
  static const Color textMuted      = textLight;

  // ── Centralized Typography Tokens (Accessible for Seniors) ────────────────
  static const TextStyle headingLarge = TextStyle(
    fontSize: 28,
    fontWeight: FontWeight.w800,
    color: textPrimary,
    letterSpacing: -0.4,
    height: 1.25,
  );

  static const TextStyle headingMedium = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w700,
    color: textPrimary,
    letterSpacing: -0.2,
    height: 1.3,
  );

  static const TextStyle titleMedium = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w700,
    color: textPrimary,
    height: 1.35,
  );

  static const TextStyle bodyConversational = TextStyle(
    fontSize: 19,
    fontWeight: FontWeight.w500,
    color: textPrimary,
    height: 1.45,
  );

  static const TextStyle bodyStandard = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w500,
    color: textPrimary,
    height: 1.4,
  );

  static const TextStyle secondaryText = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: textSecondary,
    height: 1.35,
  );

  static const TextStyle badgeText = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w700,
    color: primaryTealDark,
  );

  // ── Restrained Decoration Helpers (Anti-Vibecoding) ──────────────────────
  static BoxDecoration get cardDecoration => BoxDecoration(
    color: surfaceCard,
    borderRadius: BorderRadius.circular(14),
    border: Border.all(color: borderStone, width: 1),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withValues(alpha: 0.03),
        blurRadius: 4,
        offset: const Offset(0, 1),
      ),
    ],
  );

  /// Solid Slate Teal primary action container (replaces harsh gradients)
  static BoxDecoration tealGradientDecoration({double radius = 14}) =>
      BoxDecoration(
        color: primaryTeal,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: primaryTealDark, width: 1),
      );

  // ── ThemeData ─────────────────────────────────────────────────────────────
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: const ColorScheme.light(
        primary: primaryTeal,
        secondary: warmAmber,
        surface: background,
        error: gentleRose,
      ),
      scaffoldBackgroundColor: background,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
      ),
      textTheme: const TextTheme(
        headlineLarge: headingLarge,
        headlineMedium: headingMedium,
        titleLarge: titleMedium,
        titleMedium: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        bodyLarge: bodyConversational,
        bodyMedium: bodyStandard,
        bodySmall: secondaryText,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryTeal,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: surfaceCard,
        selectedItemColor: primaryTeal,
        unselectedItemColor: textSecondary,
        selectedLabelStyle: TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w500, fontSize: 12),
        showUnselectedLabels: true,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
    );
  }
}
