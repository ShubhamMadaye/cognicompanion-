import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';

/// Holds the patient profile and today's timeline items.
/// Uses persistent local caching and periodic background sync so that
/// updates from the Caregiver Dashboard reflect in real time.
class PatientProvider extends ChangeNotifier {
  static const _kProfileCacheKey = 'cogni_cached_patient_profile';
  static const _kTimelineCacheKey = 'cogni_cached_today_timeline';

  PatientProfile _profile = PatientProfile.mock();
  List<TodayTimelineItem> _todayTimeline = [];
  bool _isLoadingTimeline = false;
  bool _profileLoaded = false;
  Timer? _pollingTimer;
  DateTime? _lastSyncTime;

  PatientProfile get profile => _profile;
  List<TodayTimelineItem> get todayTimeline => _todayTimeline;
  bool get isLoadingTimeline => _isLoadingTimeline;
  DateTime? get lastSyncTime => _lastSyncTime;

  // ── Profile ────────────────────────────────────────────────────────────────

  Future<void> loadProfile({
    bool force = false,
    String? fallbackName,
    String? fallbackEmail,
  }) async {
    if (_profileLoaded && !force) return;

    // 1. If not yet loaded or forced, try restoring from local offline cache first
    final prefs = await SharedPreferences.getInstance();
    final cachedProfileJson = prefs.getString(_kProfileCacheKey);
    if (cachedProfileJson != null && cachedProfileJson.isNotEmpty) {
      try {
        final data = jsonDecode(cachedProfileJson) as Map<String, dynamic>;
        _profile = PatientProfile.fromJson(data);
        ApiService.defaultPatientId = _profile.id;
        notifyListeners();
      } catch (e) {
        debugPrint('[PatientProvider] Failed to decode cached profile: $e');
      }
    } else if (fallbackName != null && fallbackName.trim().isNotEmpty) {
      // Initialize with authenticated user's real name rather than generic mock
      _profile = PatientProfile(
        id: 'user-${DateTime.now().millisecondsSinceEpoch}',
        fullName: fallbackName.trim(),
        preferredLanguage: 'en',
        emergencyPhone: '+919876543210',
        emergencyName: 'Caregiver',
      );
      ApiService.defaultPatientId = _profile.id;
      notifyListeners();
    }

    // 2. Fetch live profile from backend
    final fetched = await ApiService.fetchPatientProfile();
    if (fetched != null) {
      _profile = fetched;
      ApiService.defaultPatientId = fetched.id;

      // Save to offline cache
      try {
        await prefs.setString(_kProfileCacheKey, jsonEncode(fetched.toJson()));
      } catch (e) {
        debugPrint('[PatientProvider] Failed to cache profile: $e');
      }
    } else if (fallbackName != null && fallbackName.trim().isNotEmpty) {
      _profile = _profile.copyWith(fullName: fallbackName.trim());
      try {
        await prefs.setString(_kProfileCacheKey, jsonEncode(_profile.toJson()));
      } catch (_) {}
    }

    _profileLoaded = true;
    notifyListeners();

    // Load today's schedule after profile is ready and start polling
    await loadTodayTimeline();
    startPolling();
  }

  void startPolling({Duration interval = const Duration(seconds: 15)}) {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(interval, (_) {
      silentSync();
    });
  }

  void stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }

  /// Silent background sync that refreshes timeline without flashing full screen loaders
  Future<void> silentSync() async {
    if (_profile.id.isEmpty) return;
    try {
      final items = await ApiService.fetchTodayTimeline(patientId: _profile.id);
      if (items.isNotEmpty) {
        _todayTimeline = items;
        _lastSyncTime = DateTime.now();
        notifyListeners();
        final prefs = await SharedPreferences.getInstance();
        final encodedList = jsonEncode(items.map((i) => i.toJson()).toList());
        await prefs.setString(_kTimelineCacheKey, encodedList);
      }
    } catch (e) {
      debugPrint('[PatientProvider] silentSync error: $e');
    }
  }

  void reset() {
    stopPolling();
    _profile = PatientProfile.mock();
    _todayTimeline = [];
    _isLoadingTimeline = false;
    _profileLoaded = false;
    _lastSyncTime = null;
    notifyListeners();
  }

  Future<void> clearCache() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kProfileCacheKey);
    await prefs.remove(_kTimelineCacheKey);
    reset();
  }

  void updateEmergencyContact(
      {required String name, required String phone}) async {
    _profile = _profile.copyWith(
      emergencyName: name,
      emergencyPhone: phone,
    );
    notifyListeners();

    // Update offline cache
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kProfileCacheKey, jsonEncode(_profile.toJson()));
    } catch (_) {}
  }

  // ── Today's Timeline ───────────────────────────────────────────────────────

  Future<void> loadTodayTimeline({bool silent = false}) async {
    if (!silent) {
      _isLoadingTimeline = true;
      notifyListeners();
    }

    final prefs = await SharedPreferences.getInstance();

    // 1. Try to fetch live from API
    final items = await ApiService.fetchTodayTimeline(patientId: _profile.id);
    if (items.isNotEmpty) {
      _todayTimeline = items;
      _lastSyncTime = DateTime.now();
      try {
        final encodedList = jsonEncode(items.map((i) => i.toJson()).toList());
        await prefs.setString(_kTimelineCacheKey, encodedList);
      } catch (e) {
        debugPrint('[PatientProvider] Failed to cache timeline: $e');
      }
    } else {
      // 2. Fall back to local offline cache
      final cachedJson = prefs.getString(_kTimelineCacheKey);
      if (cachedJson != null && cachedJson.isNotEmpty) {
        try {
          final decoded = jsonDecode(cachedJson) as List<dynamic>;
          _todayTimeline = decoded
              .map((d) => TodayTimelineItem.fromJson(d as Map<String, dynamic>))
              .toList();
        } catch (_) {
          _todayTimeline = TodayTimelineItem.mockItems();
        }
      } else {
        _todayTimeline = TodayTimelineItem.mockItems();
      }
    }

    if (!silent) {
      _isLoadingTimeline = false;
    }
    notifyListeners();
  }

  /// Toggle a medication item's "taken" status (optimistic update).
  void toggleItemCompleted(String itemId) async {
    final idx = _todayTimeline.indexWhere((i) => i.id == itemId);
    if (idx >= 0) {
      _todayTimeline = List.of(_todayTimeline);
      final current = _todayTimeline[idx];
      final nextCompleted = !current.isCompleted;
      final now = DateTime.now();
      final minutePad = now.minute.toString().padLeft(2, '0');
      final period = now.hour >= 12 ? 'PM' : 'AM';
      final hour12 =
          now.hour == 0 ? 12 : (now.hour > 12 ? now.hour - 12 : now.hour);
      final takenTimestamp =
          nextCompleted ? '$hour12:$minutePad $period' : null;

      _todayTimeline[idx] = current.copyWith(
        isCompleted: nextCompleted,
        takenAt: takenTimestamp,
      );
      notifyListeners();

      // Update cached timeline
      try {
        final prefs = await SharedPreferences.getInstance();
        final encodedList =
            jsonEncode(_todayTimeline.map((i) => i.toJson()).toList());
        await prefs.setString(_kTimelineCacheKey, encodedList);
      } catch (_) {}

      if (current.isMedication) {
        ApiService.logMedicationAdherence(
          patientId: _profile.id,
          medicationId: itemId,
          taken: nextCompleted,
        );
      }
    }
  }

  // ── Convenience Getters ───────────────────────────────────────────────────

  int get totalMedications =>
      _todayTimeline.where((i) => i.isMedication).length;

  int get takenMedications =>
      _todayTimeline.where((i) => i.isMedication && i.isCompleted).length;

  int get totalRoutines =>
      _todayTimeline.where((i) => i.kind == 'routine').length;
}
