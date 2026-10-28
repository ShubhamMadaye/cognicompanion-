import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';
import 'auth_service.dart';

// ─────────────────────────────────────────────────────────────────────────────
// ### 🚨 STRICT REQUIREMENT: DO NOT HARDCODE
//
// INTEGRATION RULES (enforced here):
//   Rule 1: No fake/mock data returned on API failure in production paths.
//           The ONLY acceptable offline behavior is an empty list [], null,
//           or a thrown exception that the UI turns into an error state.
//   Rule 2: API failure → surface an error or return empty. NEVER fake success.
//           submitGameSession() returning true when the backend never got the
//           data is the canonical example of what this rule prevents.
//   Rule 3: Patient identity comes from the authenticated session only.
//           No hardcoded patient UUIDs are permitted anywhere in this file.
//   Rule 4: No language-specific, patient-specific, medication-specific, or
//           family-specific text is permitted in this service layer.
// ─────────────────────────────────────────────────────────────────────────────

class ApiService {
  // ── Platform-aware base URL ───────────────────────────────────────────────
  static String get baseUrl => AuthService.baseUrl;

  // Active authenticated patient ID, dynamically set by PatientProvider or profile fetch.
  // Rule 3: Must NOT default to a hardcoded UUID string.
  static String? defaultPatientId;

  // Shared storage key — must match the key used in AuthService.
  static const _kTokenKey = 'cogni_patient_jwt';

  // ── Token helpers ─────────────────────────────────────────────────────────

  static Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kTokenKey);
  }

  static Future<Map<String, String>> _buildHeaders() async {
    final token = await _getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ── Startup Authentication ────────────────────────────────────────────────

  /// Called once on app start (before runApp).
  ///
  /// Flow:
  ///   1. Load stored JWT from SharedPreferences.
  ///   2. If found → validate via GET /auth/me.
  ///   3. If valid → done (use stored token).
  ///   4. Otherwise → login with demo credentials (POST /auth/login).
  ///   5. If backend is unreachable → continue with null token (offline mode,
  ///      show offline UI — do NOT load fake data).
  static Future<void> ensureAuthenticated() async {
    final stored = await AuthService.loadStoredToken();
    if (stored != null) {
      final valid = await AuthService.validateToken(stored);
      if (valid) {
        debugPrint('[ApiService] Existing token validated.');
        await fetchPatientProfile();
        return;
      }
      debugPrint('[ApiService] Stored token rejected. Re-authenticating...');
    }

    final token = await AuthService.loginWithDemoCredentials();
    if (token == null) {
      debugPrint('[ApiService] Backend unreachable — offline mode.');
      // Rule: do NOT fall back to mock data. Show offline state.
    } else {
      await fetchPatientProfile();
    }
  }

  // ── Patient Profile ────────────────────────────────────────────────────────
  //
  // Patient identity must always come from the authenticated session.
  // DO NOT add a hardcoded UUID fallback here.
  //
  static Future<PatientProfile?> fetchPatientProfile() async {
    try {
      final headers = await _buildHeaders();
      final url = Uri.parse('$baseUrl/patients/me');
      final response = await http
          .get(url, headers: headers)
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final profile = PatientProfile.fromJson(data);
        defaultPatientId = profile.id;
        return profile;
      }
      debugPrint('[ApiService] fetchPatientProfile: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] fetchPatientProfile error: $e');
    }
    // Return null — caller must show login/error state.
    return null;
  }

  // ── Today's Timeline ───────────────────────────────────────────────────────
  //
  // Returns [] on failure — caller must show "No items today" or an error.
  // DO NOT fall back to TodayTimelineItem.mockItems() here.
  //
  static Future<List<TodayTimelineItem>> fetchTodayTimeline({
    required String patientId,
  }) async {
    try {
      final today = DateTime.now();
      final dateStr =
          '${today.year}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';
      final headers = await _buildHeaders();
      final url =
          Uri.parse('$baseUrl/patients/$patientId/timeline?day=$dateStr');
      final response = await http
          .get(url, headers: headers)
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data
            .map((item) =>
                TodayTimelineItem.fromJson(item as Map<String, dynamic>))
            .toList();
      }
      debugPrint('[ApiService] fetchTodayTimeline: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] fetchTodayTimeline error: $e');
    }
    // Rule: return empty list. The UI shows an appropriate empty/error state.
    return [];
  }

  // ── Medication Adherence Logging ──────────────────────────────────────────
  static Future<bool> logMedicationAdherence({
    required String patientId,
    required String medicationId,
    required bool taken,
    String? notes,
  }) async {
    try {
      final now = DateTime.now();
      final dateStr =
          '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      final headers = await _buildHeaders();
      final url = Uri.parse(
          '$baseUrl/patients/$patientId/medications/$medicationId/log');
      final response = await http.post(
        url,
        headers: headers,
        body: jsonEncode({
          'log_date': dateStr,
          'taken': taken,
          'notes': notes ??
              (taken
                  ? 'Recorded by patient via app'
                  : 'Marked missed via app'),
        }),
      );
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      debugPrint('[ApiService] logMedicationAdherence error: $e');
      return false;
    }
  }

  // ── Memories & People (Live Two-Way Sync) ──────────────────────────────────
  static Future<List<Map<String, dynamic>>> fetchMemories({
    required String patientId,
    int limit = 50,
  }) async {
    try {
      final headers = await _buildHeaders();
      final url = Uri.parse('$baseUrl/patients/$patientId/memories?limit=$limit');
      final response = await http.get(url, headers: headers).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.map((item) => item as Map<String, dynamic>).toList();
      }
      debugPrint('[ApiService] fetchMemories: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] fetchMemories error: $e');
    }
    return [];
  }

  static Future<List<Map<String, dynamic>>> fetchPeople({
    required String patientId,
  }) async {
    try {
      final headers = await _buildHeaders();
      final url = Uri.parse('$baseUrl/patients/$patientId/people');
      final response = await http.get(url, headers: headers).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.map((item) => item as Map<String, dynamic>).toList();
      }
      debugPrint('[ApiService] fetchPeople: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] fetchPeople error: $e');
    }
    return [];
  }

  // ── Game Content Generation ────────────────────────────────────────────────
  //
  // Returns null on failure — game screen must show an error, not fake content.
  //
  static Future<Map<String, dynamic>?> fetchGameContent({
    required String patientId,
    required String gameType,
    String difficulty = 'MEDIUM',
  }) async {
    try {
      final headers = await _buildHeaders();
      final url = Uri.parse(
          '$baseUrl/patients/$patientId/games/$gameType/generate?difficulty=$difficulty');
      final response = await http.post(url, headers: headers);
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      debugPrint('[ApiService] fetchGameContent: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] fetchGameContent error: $e');
    }
    return null;
  }

  // ── Game Session Submission ────────────────────────────────────────────────
  //
  // Rule: returns FALSE on failure.
  //
  // DO NOT return true on a network error. The UI must show an honest error:
  //   "Your result could not be saved. Please check your connection."
  //
  // An offline queue (Phase 5) will be added later to retry failed sessions.
  // Until then, honest failure is better than silent fake success.
  //
  static Future<bool> submitGameSession({
    required String patientId,
    required String gameType,
    required String difficulty,
    required int score,
    required int totalItems,
    required int correctItems,
    required int reactionTimeMs,
    required int mistakes,
  }) async {
    try {
      final headers = await _buildHeaders();
      final url = Uri.parse('$baseUrl/patients/$patientId/games/sessions');
      final response = await http.post(
        url,
        headers: headers,
        body: jsonEncode({
          'game_type': gameType,
          'difficulty_level': difficulty,
          'score': score,
          'accuracy': totalItems > 0 ? (correctItems / totalItems) : 1.0,
          'total_items': totalItems,
          'correct_items': correctItems,
          'reaction_time_ms': reactionTimeMs,
          'mistakes': mistakes,
        }),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return true;
      }
      debugPrint(
          '[ApiService] submitGameSession failed: ${response.statusCode} — ${response.body}');
      return false;
    } catch (e) {
      // Rule: return false — the caller must display an error, not fake success.
      debugPrint('[ApiService] submitGameSession error: $e');
      return false;
    }
  }

  // ── Voice Assistant / Memory Engine Query ──────────────────────────────────
  //
  // Rule: THROWS on failure. There is no offline fallback.
  //
  // The UI must handle the exception and show an error message such as:
  //   "Unable to reach the assistant. Please check your connection."
  //
  // DO NOT add an _offlineFallback() that returns hardcoded patient names,
  // medications, family members, or visit details.
  //
  static Future<VoiceChatMessage> askAssistant({
    required String patientId,
    required String query,
    String? conversationId,
    String? languageCode,
    String? imageBase64,
  }) async {
    final headers = await _buildHeaders();
    final url =
        Uri.parse('$baseUrl/patients/$patientId/conversations/message');
    final payload = <String, dynamic>{
      'query': query,
      'conversation_id': conversationId,
      'language_code': languageCode ?? 'en',
    };
    if (imageBase64 != null && imageBase64.isNotEmpty) {
      payload['image_base64'] = imageBase64;
    }

    final response = await http.post(
      url,
      headers: headers,
      body: jsonEncode(payload),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final sourcesList = (data['sources'] as List<dynamic>?)
          ?.map((s) =>
              '${s['source_type'].toString().toUpperCase()}: ${s['title']}')
          .toList();

      return VoiceChatMessage(
        text: data['answer'] ?? data['reply'] ?? '',
        isUser: false,
        timestamp: DateTime.now(),
        intent: data['intent'],
        confidence: (data['confidence'] as num?)?.toDouble(),
        sources: sourcesList,
        conversationId: data['conversation_id']?.toString(),
        audioBase64: data['audio_base64'],
      );
    }

    // Non-200: throw so the UI shows an honest error state.
    throw Exception(
      'Assistant unavailable (${response.statusCode}). Check your connection.',
    );
  }

  // ── Audio Transcription (STT) ─────────────────────────────────────────────
  static Future<String?> transcribeAudio({
    required String patientId,
    required List<int> audioBytes,
    String filename = 'audio.wav',
    String languageCode = 'en-IN',
  }) async {
    try {
      final token = await _getToken();
      final uri = Uri.parse('$baseUrl/patients/$patientId/voice/transcribe');
      final request = http.MultipartRequest('POST', uri);
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      request.fields['language_code'] = languageCode;
      request.files.add(http.MultipartFile.fromBytes(
        'audio',
        audioBytes,
        filename: filename,
      ));

      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['transcript'] as String?;
      }
      debugPrint('[ApiService] transcribeAudio: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] transcribeAudio error: $e');
    }
    return null;
  }

  // ── Speech Synthesis (TTS) ────────────────────────────────────────────────
  static Future<String?> synthesizeSpeech({
    required String patientId,
    required String text,
    String languageCode = 'en-IN',
    double speakingRate = 0.9,
  }) async {
    try {
      final headers = await _buildHeaders();
      final url = Uri.parse('$baseUrl/patients/$patientId/voice/synthesize');
      final response = await http.post(
        url,
        headers: headers,
        body: jsonEncode({
          'text': text,
          'language_code': languageCode,
          'speaking_rate': speakingRate,
        }),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['audio_base64'] as String?;
      }
      debugPrint('[ApiService] synthesizeSpeech: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] synthesizeSpeech error: $e');
    }
    return null;
  }

  // ── End-to-End Voice Converse Turn ────────────────────────────────────────
  static Future<VoiceChatMessage?> voiceConverse({
    required String patientId,
    required List<int> audioBytes,
    String filename = 'audio.wav',
    String? conversationId,
    String languageCode = 'en-IN',
  }) async {
    try {
      final token = await _getToken();
      final uri = Uri.parse('$baseUrl/patients/$patientId/voice/converse');
      final request = http.MultipartRequest('POST', uri);
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      request.fields['language_code'] = languageCode;
      if (conversationId != null) {
        request.fields['conversation_id'] = conversationId;
      }
      request.files.add(http.MultipartFile.fromBytes(
        'audio',
        audioBytes,
        filename: filename,
      ));

      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final sourcesList = (data['sources'] as List<dynamic>?)
            ?.map((s) =>
                '${s['source_type'].toString().toUpperCase()}: ${s['title']}')
            .toList();

        return VoiceChatMessage(
          text: data['answer'] ?? data['reply'] ?? '',
          isUser: false,
          timestamp: DateTime.now(),
          intent: data['intent'],
          confidence: (data['confidence'] as num?)?.toDouble(),
          sources: sourcesList,
          conversationId: data['conversation_id']?.toString(),
          audioBase64: data['audio_base64'],
        );
      }
      debugPrint('[ApiService] voiceConverse: ${response.statusCode}');
    } catch (e) {
      debugPrint('[ApiService] voiceConverse error: $e');
    }
    return null;
  }
}
