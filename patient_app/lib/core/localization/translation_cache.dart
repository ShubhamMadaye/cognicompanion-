import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Persists translated string maps to SharedPreferences.
///
/// Key format: `l10n_cache_<locale>` → JSON-encoded Map<String,String>
/// Version key: `l10n_cache_ver_<locale>` → source-string hash for invalidation.
class TranslationCache {
  TranslationCache._();

  static const _prefix = 'l10n_cache_';
  static const _verPrefix = 'l10n_cache_ver_';

  // ── Read ────────────────────────────────────────────────────────────────────

  /// Returns cached translations for [locale], or null if nothing is cached.
  static Future<Map<String, String>?> load(String locale) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_prefix$locale');
    if (raw == null) return null;
    try {
      return Map<String, String>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return null; // corrupted entry → treat as cache miss
    }
  }

  // ── Write ───────────────────────────────────────────────────────────────────

  /// Saves [strings] for [locale].
  /// [sourceHash] is a simple fingerprint of the English source keys
  /// so stale caches can be detected after an app update adds new strings.
  static Future<void> save(
    String locale,
    Map<String, String> strings, {
    String? sourceHash,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_prefix$locale', jsonEncode(strings));
    if (sourceHash != null) {
      await prefs.setString('$_verPrefix$locale', sourceHash);
    }
  }

  // ── Invalidation ─────────────────────────────────────────────────────────────

  /// Returns true if the cache for [locale] was built with a different
  /// source hash (i.e. new strings have been added since the cache was saved).
  static Future<bool> isStale(String locale, String currentSourceHash) async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('$_verPrefix$locale');
    return saved != currentSourceHash;
  }

  /// Removes the cached translations for [locale].
  static Future<void> evict(String locale) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_prefix$locale');
    await prefs.remove('$_verPrefix$locale');
  }

  /// Clears all cached translations (all locales).
  static Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    final toRemove = prefs.getKeys()
        .where((k) => k.startsWith(_prefix) || k.startsWith(_verPrefix))
        .toList();
    for (final k in toRemove) {
      await prefs.remove(k);
    }
  }
}
