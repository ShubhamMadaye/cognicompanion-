import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Owns the authentication and JWT lifecycle for the Flutter patient app:
///   - loginWithCredentials(email, password) → POST /auth/login → stores token and user info
///   - loginWithDemoCredentials() → one-tap demo login for presentations
///   - loadStoredToken() → reads token from SharedPreferences
///   - validateToken(token) → verifies token with GET /auth/me
///   - logout() → clears SharedPreferences
class AuthService {
  // ── SharedPreferences keys ────────────────────────────────────────────────
  static const _kTokenKey = 'cogni_patient_jwt';
  static const _kUserEmailKey = 'cogni_patient_email';
  static const _kUserNameKey = 'cogni_patient_name';
  static const _kUserRoleKey = 'cogni_patient_role';
  static const _kCustomBaseUrlKey = 'cogni_custom_base_url';

  // ── Demo credentials (SIH demo ONLY — NOT for production) ──────────────────
  // SECURITY: These credentials are intentionally public for the SIH demo
  // build. Before any production deployment, remove this block and require
  // users to enter real credentials from the login screen.
  static const String demoEmail = 'patient@cognicompanion.demo';
  static const String demoPassword = 'CogniDemo2024!'; // SIH demo only


  // ── Base URL ─────────────────────────────────────────────────────────────
  static String? _customBaseUrl;
  // NOTE: Replace this with your actual LAN IP at demo time; do not commit
  // a real IP here as it leaks network topology.
  static const String defaultServerIp = '192.168.1.x'; // set at demo time

  static Future<void> initBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    _customBaseUrl = prefs.getString(_kCustomBaseUrlKey);
  }

  static Future<void> setCustomBaseUrl(String? url) async {
    final prefs = await SharedPreferences.getInstance();
    if (url == null || url.trim().isEmpty) {
      _customBaseUrl = null;
      await prefs.remove(_kCustomBaseUrlKey);
    } else {
      var sanitized = url.trim();
      if (!sanitized.startsWith('http://') && !sanitized.startsWith('https://')) {
        sanitized = 'http://$sanitized';
      }
      if (!sanitized.endsWith('/api/v1')) {
        sanitized = sanitized.endsWith('/') ? '${sanitized}api/v1' : '$sanitized/api/v1';
      }
      _customBaseUrl = sanitized;
      await prefs.setString(_kCustomBaseUrlKey, sanitized);
    }
  }

  static String get baseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) {
      return _customBaseUrl!;
    }
    const fromEnv = String.fromEnvironment('API_URL');
    if (fromEnv.isNotEmpty) return fromEnv;

    if (kIsWeb ||
        defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.macOS ||
        defaultTargetPlatform == TargetPlatform.linux) {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return 'http://$defaultServerIp:8000/api/v1';
  }

  /// Ping the backend /health endpoint to check server availability.
  static Future<bool> testConnection([String? targetUrl]) async {
    try {
      final base = targetUrl ?? baseUrl;
      final root = base.replaceAll(RegExp(r'/api/v1/?$'), '');
      final url = Uri.parse('$root/health');
      final response = await http.get(url).timeout(const Duration(seconds: 3));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /// Register a new user account (PATIENT or CAREGIVER) with the backend.
  static Future<Map<String, dynamic>?> registerWithCredentials({
    required String fullName,
    required String email,
    required String password,
    String role = 'PATIENT',
  }) async {
    try {
      final url = Uri.parse('$baseUrl/auth/register');
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'full_name': fullName.trim(),
              'email': email.trim(),
              'password': password,
              'role': role,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final token = data['access_token'] as String?;
        if (token != null && token.isNotEmpty) {
          await _storeToken(token);

          // Store user metadata if provided
          if (data['user'] is Map<String, dynamic>) {
            final user = data['user'] as Map<String, dynamic>;
            final prefs = await SharedPreferences.getInstance();
            await prefs.setString(_kUserEmailKey, user['email']?.toString() ?? email);
            await prefs.setString(_kUserNameKey, user['full_name']?.toString() ?? fullName);
            await prefs.setString(_kUserRoleKey, user['role']?.toString() ?? role);
          }

          debugPrint('[AuthService] Registration successful for $email. Token stored.');
          return data;
        }
      } else {
        final err = jsonDecode(response.body);
        final detail = err is Map ? err['detail'] : 'Registration failed';
        throw Exception(detail?.toString() ?? 'Registration failed');
      }
    } catch (e) {
      debugPrint('[AuthService] Registration exception: $e');
      rethrow;
    }
    return null;
  }

  /// Login with user-provided credentials.
  /// Returns a Map with access_token and user info, or throws an exception on error.
  static Future<Map<String, dynamic>?> loginWithCredentials(
    String email,
    String password,
  ) async {
    try {
      final url = Uri.parse('$baseUrl/auth/login');
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'email': email.trim(),
              'password': password,
            }),
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final token = data['access_token'] as String?;
        if (token != null && token.isNotEmpty) {
          await _storeToken(token);

          // Store user metadata if provided
          if (data['user'] is Map<String, dynamic>) {
            final user = data['user'] as Map<String, dynamic>;
            final prefs = await SharedPreferences.getInstance();
            await prefs.setString(_kUserEmailKey, user['email']?.toString() ?? email);
            await prefs.setString(_kUserNameKey, user['full_name']?.toString() ?? '');
            await prefs.setString(_kUserRoleKey, user['role']?.toString() ?? 'PATIENT');
          }

          debugPrint('[AuthService] Login successful for $email. Token stored.');
          return data;
        }
      } else {
        final err = jsonDecode(response.body);
        final detail = err is Map ? err['detail'] : 'Login failed';
        throw Exception(detail?.toString() ?? 'Invalid credentials');
      }
    } catch (e) {
      debugPrint('[AuthService] Login exception: $e');
      rethrow;
    }
    return null;
  }

  /// Attempt login with demo credentials.
  /// Returns the JWT string on success, null on failure.
  static Future<String?> loginWithDemoCredentials() async {
    try {
      final data = await loginWithCredentials(demoEmail, demoPassword);
      return data?['access_token'] as String?;
    } catch (e) {
      debugPrint('[AuthService] Demo login error (backend unreachable?): $e');
      return null;
    }
  }

  /// Load a previously stored JWT from SharedPreferences.
  /// Returns null if no token is stored.
  static Future<String?> loadStoredToken() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_kTokenKey);
    if (token != null && token.isNotEmpty) {
      debugPrint('[AuthService] Loaded stored token from SharedPreferences.');
      return token;
    }
    return null;
  }

  /// Validate the stored token by calling /auth/me.
  /// Returns true if the server accepts it.
  static Future<bool> validateToken(String token) async {
    try {
      final url = Uri.parse('$baseUrl/auth/me');
      final response = await http
          .get(url, headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          })
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Retrieve cached user information.
  static Future<Map<String, String?>> getCachedUser() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'email': prefs.getString(_kUserEmailKey),
      'name': prefs.getString(_kUserNameKey),
      'role': prefs.getString(_kUserRoleKey),
    };
  }

  /// Clear all stored auth state (logout).
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kTokenKey);
    await prefs.remove(_kUserEmailKey);
    await prefs.remove(_kUserNameKey);
    await prefs.remove(_kUserRoleKey);
    debugPrint('[AuthService] Token and auth state cleared.');
  }

  // ── Private ───────────────────────────────────────────────────────────────

  static Future<void> _storeToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kTokenKey, token);
  }
}
