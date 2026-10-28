import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../localization/app_localizations.dart';
import '../localization/localization_service.dart';
import '../localization/translation_cache.dart';

const _kLocaleKey = 'app_locale';

/// Manages the active language and exposes [tr] for synchronous string lookup.
///
/// Flow when the user switches language:
///   1. Set [isLoading] = true → notifyListeners() (UI may show a subtle indicator)
///   2. Check TranslationCache for the locale
///   3a. Cache hit  → load immediately
///   3b. Cache miss → call LocalizationService.translate()
///        → on success: save to cache, use result
///        → on failure: fall back to English
///   4. Set [isLoading] = false → notifyListeners() (UI rebuilds with new strings)
///
/// UI widgets stay fully synchronous:
///   Text(context.watch<LocalizationProvider>().tr('tap_to_talk'))
class LocalizationProvider extends ChangeNotifier {
  // ── State ──────────────────────────────────────────────────────────────────

  String _locale = 'en';
  bool _isLoading = false;

  /// English source strings, loaded once from assets/l10n/en.json.
  Map<String, String> _englishSource = {};

  /// Active translated strings for the current locale.
  /// Falls back to [_englishSource] if a key is missing.
  Map<String, String> _active = {};

  // ── Getters ────────────────────────────────────────────────────────────────

  String get locale => _locale;

  /// True while a translation fetch is in progress.
  bool get isLoading => _isLoading;

  /// Native name of the current language (e.g. "हिन्दी").
  String get localeName =>
      AppLocalizations.metaFor(_locale)?['nativeName'] ?? 'English';

  // ── Core API ───────────────────────────────────────────────────────────────

  /// Synchronous translation lookup — safe to call directly inside Text().
  String tr(String key) =>
      _active[key] ?? _englishSource[key] ?? key;

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  /// Call once from main() before runApp().
  /// Loads English source strings, then restores the saved locale.
  Future<void> init() async {
    // 1. Load English source (always available, bundled in app).
    _englishSource = await AppLocalizations.loadEnglishSource();
    _active = Map.from(_englishSource);

    // 2. Restore saved locale.
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_kLocaleKey) ?? 'en';
    if (saved != 'en') {
      // Load silently — no loading spinner at cold-start.
      await _load(saved, silent: true);
    }
  }

  /// Switch to [localeCode] and persist the choice.
  /// Shows [isLoading] = true while fetching if not already cached.
  Future<void> setLocale(String localeCode) async {
    if (!_isSupported(localeCode)) return;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLocaleKey, localeCode);

    if (localeCode == _locale) return;

    _locale = localeCode;

    if (localeCode == 'en') {
      _active = Map.from(_englishSource);
      notifyListeners();
    } else {
      await _load(localeCode);
    }
  }

  // ── Private ────────────────────────────────────────────────────────────────

  Future<void> _load(String localeCode, {bool silent = false}) async {
    final hash = AppLocalizations.sourceHash(_englishSource);

    // Check cache first.
    final isStale = await TranslationCache.isStale(localeCode, hash);
    if (!isStale) {
      final cached = await TranslationCache.load(localeCode);
      if (cached != null) {
        _active = _merge(_englishSource, cached);
        if (!silent) notifyListeners();
        return;
      }
    }

    // Cache miss or stale → fetch from translation API.
    if (!silent) {
      _isLoading = true;
      notifyListeners();
    }

    try {
      final translated = await LocalizationService.translate(
        _englishSource,
        localeCode,
      );
      if (translated != null) {
        _active = _merge(_englishSource, translated);
        await TranslationCache.save(localeCode, translated, sourceHash: hash);
      } else {
        // Unsupported locale (e.g. Bodo) → stay on English.
        _active = Map.from(_englishSource);
      }
    } catch (_) {
      // Network error → fall back to English silently.
      _active = Map.from(_englishSource);
    }

    _isLoading = false;
    notifyListeners();
  }

  /// Merges [source] with [translated], filling any missing translated keys
  /// with the English fallback so widgets never see an empty string.
  Map<String, String> _merge(
    Map<String, String> source,
    Map<String, String> translated,
  ) {
    return {
      for (final key in source.keys)
        key: (translated[key]?.isNotEmpty == true)
            ? translated[key]!
            : source[key]!,
    };
  }

  bool _isSupported(String code) =>
      AppLocalizations.supportedLocales.any((l) => l['code'] == code);
}
