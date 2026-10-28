import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum TextScaleLevel {
  normal,
  large,
  extraLarge,
}

class AccessibilityProvider extends ChangeNotifier {
  static const String _kSimpleModeKey = 'cogni_simple_mode';
  static const String _kTextScaleKey = 'cogni_text_scale';
  static const String _kHighContrastKey = 'cogni_high_contrast';
  static const String _kHapticKey = 'cogni_haptic';
  static const String _kVoiceRateKey = 'cogni_voice_rate';
  static const String _kNotifyMedKey = 'cogni_notify_med';
  static const String _kNotifyRoutineKey = 'cogni_notify_routine';
  static const String _kNotifyCheckinsKey = 'cogni_notify_checkins';

  bool _isSimpleMode = false;
  TextScaleLevel _textScaleLevel = TextScaleLevel.normal;
  bool _isHighContrast = false;
  bool _hapticEnabled = true;
  double _voiceSpeakingRate = 0.50; // 0.40 - 0.70

  // Notification Preferences
  bool _notifyMedication = true;
  bool _notifyRoutine = true;
  bool _notifyCheckins = true;

  bool get isSimpleMode => _isSimpleMode;
  TextScaleLevel get textScaleLevel => _textScaleLevel;
  bool get isHighContrast => _isHighContrast;
  bool get hapticEnabled => _hapticEnabled;
  double get voiceSpeakingRate => _voiceSpeakingRate;

  bool get notifyMedication => _notifyMedication;
  bool get notifyRoutine => _notifyRoutine;
  bool get notifyCheckins => _notifyCheckins;

  double get textScale {
    if (_isSimpleMode) return 1.25;
    switch (_textScaleLevel) {
      case TextScaleLevel.normal:
        return 1.0;
      case TextScaleLevel.large:
        return 1.18;
      case TextScaleLevel.extraLarge:
        return 1.35;
    }
  }

  String get textScaleLabel {
    switch (_textScaleLevel) {
      case TextScaleLevel.normal:
        return 'Default (100%)';
      case TextScaleLevel.large:
        return 'Large (118%)';
      case TextScaleLevel.extraLarge:
        return 'Extra Large (135%)';
    }
  }

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _isSimpleMode = prefs.getBool(_kSimpleModeKey) ?? false;
    _isHighContrast = prefs.getBool(_kHighContrastKey) ?? false;
    _hapticEnabled = prefs.getBool(_kHapticKey) ?? true;
    _voiceSpeakingRate = prefs.getDouble(_kVoiceRateKey) ?? 0.50;

    final scaleIndex = prefs.getInt(_kTextScaleKey) ?? 0;
    if (scaleIndex >= 0 && scaleIndex < TextScaleLevel.values.length) {
      _textScaleLevel = TextScaleLevel.values[scaleIndex];
    }

    _notifyMedication = prefs.getBool(_kNotifyMedKey) ?? true;
    _notifyRoutine = prefs.getBool(_kNotifyRoutineKey) ?? true;
    _notifyCheckins = prefs.getBool(_kNotifyCheckinsKey) ?? true;

    notifyListeners();
  }

  Future<void> setSimpleMode(bool enabled) async {
    if (_isSimpleMode == enabled) return;
    _isSimpleMode = enabled;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kSimpleModeKey, enabled);
  }

  Future<void> setTextScaleLevel(TextScaleLevel level) async {
    if (_textScaleLevel == level) return;
    _textScaleLevel = level;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kTextScaleKey, level.index);
  }

  Future<void> setHighContrast(bool enabled) async {
    if (_isHighContrast == enabled) return;
    _isHighContrast = enabled;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kHighContrastKey, enabled);
  }

  Future<void> setHapticEnabled(bool enabled) async {
    if (_hapticEnabled == enabled) return;
    _hapticEnabled = enabled;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kHapticKey, enabled);
  }

  Future<void> setVoiceSpeakingRate(double rate) async {
    _voiceSpeakingRate = rate.clamp(0.35, 0.85);
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_kVoiceRateKey, _voiceSpeakingRate);
  }

  Future<void> setNotificationPref({
    bool? medication,
    bool? routine,
    bool? checkins,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (medication != null) {
      _notifyMedication = medication;
      await prefs.setBool(_kNotifyMedKey, medication);
    }
    if (routine != null) {
      _notifyRoutine = routine;
      await prefs.setBool(_kNotifyRoutineKey, routine);
    }
    if (checkins != null) {
      _notifyCheckins = checkins;
      await prefs.setBool(_kNotifyCheckinsKey, checkins);
    }
    notifyListeners();
  }
}
