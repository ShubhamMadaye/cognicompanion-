import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/theme/app_theme.dart';
import 'core/providers/accessibility_provider.dart';
import 'core/providers/auth_provider.dart';
import 'core/providers/patient_provider.dart';
import 'core/providers/localization_provider.dart';
import 'screens/language_selection_screen.dart';
import 'screens/main_scaffold.dart';
import 'screens/login_screen.dart';
import 'services/auth_service.dart';

Future<void> main() async {
  // Ensure Flutter bindings are initialized before any async work.
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize saved backend server configuration
  await AuthService.initBaseUrl();

  // Load accessibility / Simple Mode preferences.
  final accessibilityProvider = AccessibilityProvider();
  await accessibilityProvider.init();

  // Load English source strings + restore saved language preference.
  final localizationProvider = LocalizationProvider();
  await localizationProvider.init();

  // Initialize authentication provider and verify stored session.
  final authProvider = AuthProvider();
  await authProvider.checkAuthStatus();

  // Check if user has chosen their initial language
  final prefs = await SharedPreferences.getInstance();
  final bool hasChosenInitialLanguage =
      prefs.getBool('has_chosen_initial_language') ?? false;

  // Global Production Error Boundary: Prevent unhandled crashes
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    debugPrint('[CogniCompanion CrashShield] UI Exception: ${details.exceptionAsString()}');
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    debugPrint('[CogniCompanion CrashShield] Async Exception: $error');
    return true; // Mark as handled to prevent process termination
  };

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: accessibilityProvider),
        ChangeNotifierProvider.value(value: authProvider),
        ChangeNotifierProvider(create: (_) => PatientProvider()),
        ChangeNotifierProvider.value(value: localizationProvider),
      ],
      child: CogniCompanionPatientApp(
        hasChosenInitialLanguage: hasChosenInitialLanguage,
      ),
    ),
  );
}

class CogniCompanionPatientApp extends StatefulWidget {
  final bool hasChosenInitialLanguage;

  const CogniCompanionPatientApp({
    super.key,
    this.hasChosenInitialLanguage = true,
  });

  @override
  State<CogniCompanionPatientApp> createState() =>
      _CogniCompanionPatientAppState();
}

class _CogniCompanionPatientAppState extends State<CogniCompanionPatientApp> {
  late bool _hasChosenLanguage;

  @override
  void initState() {
    super.initState();
    _hasChosenLanguage = widget.hasChosenInitialLanguage;
  }

  void _handleLanguageConfirmed() {
    setState(() {
      _hasChosenLanguage = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final accessibility = context.watch<AccessibilityProvider>();

    return MaterialApp(
      title: 'CogniCompanion',
      theme: AppTheme.lightTheme,
      builder: (context, child) {
        ErrorWidget.builder = (FlutterErrorDetails errorDetails) {
          return const Scaffold(
            backgroundColor: AppTheme.background,
            body: Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.favorite_rounded,
                        size: 48, color: AppTheme.primaryTeal),
                    SizedBox(height: 16),
                    Text(
                      'CogniCompanion is right here with you.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'A brief hiccup occurred. The app is continuing safely.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        };
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(accessibility.textScale),
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: _hasChosenLanguage
          ? const AuthGate()
          : LanguageSelectionScreen(
              isOnboarding: true,
              onConfirmed: _handleLanguageConfirmed,
            ),
      debugShowCheckedModeBanner: false,
    );
  }
}

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = context.read<AuthProvider>();
      if (auth.isAuthenticated) {
        context.read<PatientProvider>().loadProfile();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (auth.isLoading) {
      return Scaffold(
        backgroundColor: AppTheme.background,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 76,
                height: 76,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.06),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Image.asset(
                  'assets/images/app_logo.png',
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => const Icon(
                    Icons.favorite_rounded,
                    color: AppTheme.primaryTeal,
                    size: 38,
                  ),
                ),
              ),
              const SizedBox(height: 20),
              const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: AppTheme.primaryTeal,
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (auth.isAuthenticated) {
      return const MainScaffold();
    }

    return const LoginScreen();
  }
}
