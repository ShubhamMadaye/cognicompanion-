import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;

/// Metadata and loading helpers for the localization system.
///
/// Translation data is no longer stored here. Instead:
///   • English strings live in  assets/l10n/en.json  (single source of truth)
///   • Other languages are fetched dynamically via LocalizationService
///   • Results are cached in SharedPreferences via TranslationCache
///
/// UI usage (synchronous, no async in widgets):
///   final l = context.watch<LocalizationProvider>();
///   Text(l.tr('tap_to_talk'))
class AppLocalizations {
  AppLocalizations._();

  // ── Supported locales ────────────────────────────────────────────────────────
  // Shown in the language picker, in display order.

  static const List<Map<String, String>> supportedLocales = [
    // ── Main Indian Languages ─────────────────────────────────────────────────
    {'code': 'en',  'name': 'English',    'nativeName': 'English',      'flag': '🇮🇳'},
    {'code': 'hi',  'name': 'Hindi',      'nativeName': 'हिन्दी',        'flag': '🇮🇳'},
    {'code': 'mr',  'name': 'Marathi',    'nativeName': 'मराठी',         'flag': '🇮🇳'},
    {'code': 'bn',  'name': 'Bengali',    'nativeName': 'বাংলা',         'flag': '🇮🇳'},
    {'code': 'ta',  'name': 'Tamil',      'nativeName': 'தமிழ்',         'flag': '🇮🇳'},
    {'code': 'te',  'name': 'Telugu',     'nativeName': 'తెలుగు',        'flag': '🇮🇳'},
    {'code': 'kn',  'name': 'Kannada',    'nativeName': 'ಕನ್ನಡ',         'flag': '🇮🇳'},
    {'code': 'gu',  'name': 'Gujarati',   'nativeName': 'ગુજરાતી',       'flag': '🇮🇳'},
    {'code': 'pa',  'name': 'Punjabi',    'nativeName': 'ਪੰਜਾਬੀ',        'flag': '🇮🇳'},
    {'code': 'ml',  'name': 'Malayalam',  'nativeName': 'മലയാളം',        'flag': '🇮🇳'},
    // ── North East Indian Languages ──────────────────────────────────────────
    {'code': 'as',  'name': 'Assamese',   'nativeName': 'অসমীয়া',       'flag': '🇮🇳', 'tier': 'Tier 1 — Full Voice'},
    {'code': 'ne',  'name': 'Nepali',     'nativeName': 'नेपाली',        'flag': '🇮🇳', 'tier': 'Full Voice'},
    {'code': 'brx', 'name': 'Bodo',       'nativeName': 'बड़ो',           'flag': '🇮🇳', 'tier': 'Text Assistance'},
    {'code': 'mni', 'name': 'Meitei',     'nativeName': 'ꯃꯩꯇꯩꯂꯣꯟ',       'flag': '🇮🇳', 'tier': 'Tier 2 — Voice + Screen'},
    {'code': 'lus', 'name': 'Mizo',       'nativeName': 'Mizo ṭawng',   'flag': '🇮🇳', 'tier': 'Tier 2 — Voice + Screen'},
    {'code': 'kha', 'name': 'Khasi',      'nativeName': 'Ka Ktien Khasi','flag': '🇮🇳', 'tier': 'Tier 2 — Voice + Screen'},
    {'code': 'grt', 'name': 'Garo',       'nativeName': 'A·chik',       'flag': '🇮🇳', 'tier': 'Tier 3 — Text Response'},
    {'code': 'trp', 'name': 'Kokborok',   'nativeName': 'Kokborok',     'flag': '🇮🇳', 'tier': 'Tier 3 — Text Response'},
    {'code': 'nag', 'name': 'Nagamese',   'nativeName': 'Nagamese',     'flag': '🇮🇳', 'tier': 'Tier 3 — Text Response'},
    {'code': 'njz', 'name': 'Nyishi',     'nativeName': 'Nyishi',       'flag': '🇮🇳', 'tier': 'Tier 4 — Experimental'},
    {'code': 'pbv', 'name': 'Pnar',       'nativeName': 'Pnar',         'flag': '🇮🇳', 'tier': 'Tier 3 — Text Response'},
  ];

  // ── Asset loader ─────────────────────────────────────────────────────────────

  /// Loads the English source strings from assets/l10n/en.json.
  /// Called once at startup by LocalizationProvider.init().
  static Future<Map<String, String>> loadEnglishSource() async {
    final raw = await rootBundle.loadString('assets/l10n/en.json');
    return Map<String, String>.from(jsonDecode(raw) as Map);
  }

  // ── Utilities ────────────────────────────────────────────────────────────────

  /// Returns a cheap hash of the source-map keys, used to detect when
  /// new strings are added after a cache was written (cache invalidation).
  static String sourceHash(Map<String, String> source) {
    final keys = source.keys.toList()..sort();
    return keys.join(',').hashCode.toString();
  }

  /// Returns the display metadata for [code], or null.
  static Map<String, String>? metaFor(String code) {
    try {
      return supportedLocales.firstWhere((l) => l['code'] == code);
    } catch (_) {
      return null;
    }
  }
}
