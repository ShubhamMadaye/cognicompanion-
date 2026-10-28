import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;
import 'package:http/http.dart' as http;

/// Locale codes that are bundled as local JSON assets in assets/l10n/
/// All supported Indian and North-Eastern languages are bundled for instant, 100% offline access.
const _bundledLocales = {
  'en', 'hi', 'mr', 'bn', 'ta', 'te', 'kn', 'gu', 'pa', 'ml',
  'as', 'ne', 'brx', 'mni', 'lus', 'kha',
};

/// Maps our internal locale codes to the BCP-47 codes used by Google Translate.
const _googleLangMap = {
  'en':  'en',
  'hi':  'hi',
  'mr':  'mr',
  'bn':  'bn',
  'ta':  'ta',
  'te':  'te',
  'kn':  'kn',
  'gu':  'gu',
  'pa':  'pa',
  'ml':  'ml',
  'as':  'as',   // Also has bundled JSON for offline/cold-start
  'ne':  'ne',
};

/// Translates a batch of English strings into [targetLocale] using either:
///  • A bundled JSON asset (for NE languages not covered by the free API)
///  • The Google Translate unofficial endpoint (no API key required)
class LocalizationService {
  LocalizationService._();

  static const _separator = '\n||||\n';
  static const _timeout = Duration(seconds: 15);
  static final _client = http.Client();

  static bool isBundled(String locale) => _bundledLocales.contains(locale);

  /// Returns translated strings or null on unrecoverable error.
  static Future<Map<String, String>?> translate(
    Map<String, String> source,
    String targetLocale,
  ) async {
    // 1. Use bundled asset for NE languages with no API support.
    if (_bundledLocales.contains(targetLocale)) {
      return _loadBundled(targetLocale);
    }

    // 2. Use Google Translate for major Indian languages.
    final googleCode = _googleLangMap[targetLocale];
    if (googleCode == null) return null;

    final keys = source.keys.toList();
    final values = keys.map((k) => source[k]!).toList();

    // Batch all strings into one request joined by a sentinel.
    final batch = values.join(_separator);

    try {
      final translated = await _fetchTranslation(batch, googleCode);
      if (translated == null) return null;

      final parts = translated.split(_separator);
      if (parts.length != keys.length) {
        // Sentinel got translated — retry key by key (slower, but reliable).
        return await _translateOneByOne(source, googleCode);
      }

      return {for (var i = 0; i < keys.length; i++) keys[i]: parts[i].trim()};
    } catch (_) {
      return null;
    }
  }

  // ── Private helpers ─────────────────────────────────────────────────────────

  /// Loads translations from a bundled asset file.
  static Future<Map<String, String>?> _loadBundled(String locale) async {
    try {
      final raw = await rootBundle.loadString('assets/l10n/$locale.json');
      return Map<String, String>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return null; // file not found → caller falls back to English
    }
  }

  /// Calls the Google Translate unofficial gtx endpoint.
  /// Returns the translated text or null on failure.
  static Future<String?> _fetchTranslation(String text, String targetLang) async {
    final uri = Uri.parse(
      'https://translate.googleapis.com/translate_a/single'
      '?client=gtx&sl=en&tl=$targetLang&dt=t&q=${Uri.encodeComponent(text)}',
    );

    final response = await _client.get(uri).timeout(_timeout);
    if (response.statusCode != 200) return null;

    // The response is a nested JSON array.
    // result[0] is a list of [translated_chunk, source_chunk] pairs.
    final json = jsonDecode(response.body);
    final sb = StringBuffer();
    for (final chunk in json[0] as List) {
      sb.write((chunk as List)[0]);
    }
    return sb.toString();
  }

  /// Fallback: translate each key individually.
  /// Used when the batch sentinel gets mutated during translation.
  static Future<Map<String, String>?> _translateOneByOne(
    Map<String, String> source,
    String googleCode,
  ) async {
    final result = <String, String>{};
    for (final entry in source.entries) {
      final t = await _fetchTranslation(entry.value, googleCode);
      result[entry.key] = t?.trim() ?? entry.value; // fallback to English
    }
    return result;
  }
}
