import 'package:flutter/foundation.dart';
import '../../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  bool _isAuthenticated = false;
  bool _isLoading = true;
  bool _isOfflineMode = false;
  String? _userEmail;
  String? _userName;
  String? _userRole;

  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  bool get isOfflineMode => _isOfflineMode;
  String? get userEmail => _userEmail;
  String? get userName => _userName;
  String? get userRole => _userRole;

  /// Check stored authentication session on startup.
  Future<void> checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();

    final storedToken = await AuthService.loadStoredToken();
    if (storedToken != null) {
      final isValid = await AuthService.validateToken(storedToken);
      if (isValid) {
        final cached = await AuthService.getCachedUser();
        _userEmail = cached['email'];
        _userName = cached['name'];
        _userRole = cached['role'];
        _isAuthenticated = true;
        _isOfflineMode = false;
        _isLoading = false;
        notifyListeners();
        return;
      }
    }

    _isAuthenticated = false;
    _isLoading = false;
    notifyListeners();
  }

  /// Sign in with custom credentials.
  Future<void> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();

    try {
      final res = await AuthService.loginWithCredentials(email, password);
      if (res != null) {
        final cached = await AuthService.getCachedUser();
        _userEmail = cached['email'] ?? email;
        _userName = cached['name'];
        _userRole = cached['role'];
        _isAuthenticated = true;
        _isOfflineMode = false;
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Register a new account (Patient or Caregiver).
  Future<void> register({
    required String fullName,
    required String email,
    required String password,
    String role = 'PATIENT',
  }) async {
    _isLoading = true;
    notifyListeners();

    try {
      final res = await AuthService.registerWithCredentials(
        fullName: fullName,
        email: email,
        password: password,
        role: role,
      );
      if (res != null) {
        final cached = await AuthService.getCachedUser();
        _userEmail = cached['email'] ?? email;
        _userName = cached['name'] ?? fullName;
        _userRole = cached['role'] ?? role;
        _isAuthenticated = true;
        _isOfflineMode = false;
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// One-tap demo patient login for SIH presentation.
  Future<void> loginDemo() async {
    _isLoading = true;
    notifyListeners();

    try {
      final token = await AuthService.loginWithDemoCredentials();
      if (token != null) {
        _userEmail = AuthService.demoEmail;
        _userName = 'Shanti Sharma';
        _userRole = 'PATIENT';
        _isAuthenticated = true;
        _isOfflineMode = false;
      } else {
        // Backend offline — enter offline fallback mode so the demo doesn't fail
        _userEmail = AuthService.demoEmail;
        _userName = 'Shanti Sharma (Offline)';
        _userRole = 'PATIENT';
        _isAuthenticated = true;
        _isOfflineMode = true;
      }
    } catch (_) {
      // Offline fallback
      _userEmail = AuthService.demoEmail;
      _userName = 'Shanti Sharma (Offline)';
      _userRole = 'PATIENT';
      _isAuthenticated = true;
      _isOfflineMode = true;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Enter offline mode directly for offline usage.
  void enterOfflineMode() {
    _userEmail = 'offline@cognicompanion.local';
    _userName = 'Offline Patient';
    _userRole = 'PATIENT';
    _isAuthenticated = true;
    _isOfflineMode = true;
    notifyListeners();
  }

  /// Clear session and return to login screen.
  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();

    await AuthService.logout();
    _isAuthenticated = false;
    _isOfflineMode = false;
    _userEmail = null;
    _userName = null;
    _userRole = null;
    _isLoading = false;
    notifyListeners();
  }
}
