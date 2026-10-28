import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/theme/app_theme.dart';
import '../core/localization/app_localizations.dart';
import '../core/providers/localization_provider.dart';
import '../main.dart';

class LanguageSelectionScreen extends StatefulWidget {
  final bool isOnboarding;
  final VoidCallback? onConfirmed;

  const LanguageSelectionScreen({
    super.key,
    this.isOnboarding = false,
    this.onConfirmed,
  });

  @override
  State<LanguageSelectionScreen> createState() =>
      _LanguageSelectionScreenState();
}

class _LanguageSelectionScreenState extends State<LanguageSelectionScreen> {
  late String _selectedCode;
  bool _isConfirming = false;

  @override
  void initState() {
    super.initState();
    _selectedCode = context.read<LocalizationProvider>().locale;
  }

  Future<void> _handleConfirm() async {
    if (_isConfirming) return;
    setState(() => _isConfirming = true);
    HapticFeedback.mediumImpact();

    final loc = context.read<LocalizationProvider>();

    try {
      // 1. Mark initial language chosen FIRST so state is persisted immediately
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('has_chosen_initial_language', true);

      // 2. Set the selected locale without blocking navigation if slow
      await loc.setLocale(_selectedCode).timeout(
        const Duration(seconds: 1, milliseconds: 500),
        onTimeout: () {},
      );
    } catch (e) {
      debugPrint('Language confirmation note: $e');
    }

    if (!mounted) return;

    // 3. Move ahead smoothly
    if (widget.isOnboarding) {
      if (widget.onConfirmed != null) {
        widget.onConfirmed!();
      } else {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => const AuthGate()),
          (route) => false,
        );
      }
    } else {
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    const locales = AppLocalizations.supportedLocales;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        elevation: 0,
        automaticallyImplyLeading: !widget.isOnboarding,
        leading: widget.isOnboarding
            ? null
            : IconButton(
                icon: const Icon(Icons.arrow_back_ios_new_rounded,
                    color: AppTheme.textPrimary),
                onPressed: () => Navigator.pop(context),
              ),
        title: Text(
          widget.isOnboarding ? 'CogniCompanion' : l.tr('select_language'),
          style: AppTheme.headingMedium,
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Welcoming banner
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 16),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.borderSubtle),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: AppTheme.primaryTealLight,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.borderStone),
                      ),
                      child: const Icon(
                        Icons.translate_rounded,
                        color: AppTheme.primaryTealDark,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 14),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Choose Your Language',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w800,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          SizedBox(height: 2),
                          Text(
                            'अपनी भाषा चुनें • Choose anytime later',
                            style: TextStyle(
                              fontSize: 13,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // 2-Column Grid of Languages
            Expanded(
              child: GridView.builder(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.30,
                ),
                itemCount: locales.length,
                itemBuilder: (context, index) {
                  final loc = locales[index];
                  final code = loc['code'] ?? 'en';
                  final native = loc['nativeName'] ?? '';
                  final english = loc['name'] ?? '';
                  final isSelected = _selectedCode == code;

                  return GestureDetector(
                    onTap: () {
                      HapticFeedback.selectionClick();
                      setState(() => _selectedCode = code);
                    },
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 150),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppTheme.primaryTealLight
                            : Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: isSelected
                              ? AppTheme.primaryTeal
                              : AppTheme.borderSubtle,
                          width: isSelected ? 1.8 : 1.0,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isSelected ? AppTheme.primaryTeal : AppTheme.warmSurface,
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: AppTheme.borderStone),
                                ),
                                child: Text(
                                  code.toUpperCase(),
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 0.5,
                                    color: isSelected ? Colors.white : AppTheme.textSecondary,
                                  ),
                                ),
                              ),
                              if (isSelected)
                                const Icon(
                                  Icons.check_circle_rounded,
                                  color: AppTheme.primaryTeal,
                                  size: 18,
                                ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            native,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: isSelected
                                  ? FontWeight.w800
                                  : FontWeight.w600,
                              color: isSelected
                                  ? AppTheme.primaryTealDark
                                  : AppTheme.textPrimary,
                            ),
                          ),
                          Text(
                            english,
                            style: TextStyle(
                              fontSize: 12,
                              color: isSelected
                                  ? AppTheme.primaryTeal
                                  : AppTheme.textSecondary,
                            ),
                          ),
                          if (loc['tier'] != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 3),
                              child: Text(
                                loc['tier']!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w500,
                                  color: isSelected
                                      ? AppTheme.primaryTealDark
                                      : AppTheme.textMuted,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

            // Confirm Button
            Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: AppTheme.borderSubtle)),
              ),
              child: SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _isConfirming ? null : _handleConfirm,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryTeal,
                    foregroundColor: Colors.white,
                    disabledBackgroundColor:
                        AppTheme.primaryTeal.withValues(alpha: 0.7),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: _isConfirming
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _getContinueButtonText(_selectedCode),
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Icon(Icons.arrow_forward_rounded, size: 20),
                          ],
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getContinueButtonText(String code) {
    switch (code) {
      case 'hi':
        return 'जारी रखें (Continue)';
      case 'mr':
        return 'पुढे चला (Continue)';
      case 'bn':
        return 'এগিয়ে যান (Continue)';
      case 'ta':
        return 'தொடரவும் (Continue)';
      case 'te':
        return 'కొనసాగించండి (Continue)';
      case 'kn':
        return 'ಮುಂದುವರಿಸಿ (Continue)';
      case 'gu':
        return 'આગળ વધો (Continue)';
      case 'pa':
        return 'ਜਾਰੀ ਰੱਖੋ (Continue)';
      case 'ml':
        return 'തുടരുക (Continue)';
      case 'as':
        return 'অব্যাহত ৰাখক (Continue)';
      case 'ne':
        return 'जारी राख्नुहोस् (Continue)';
      default:
        return 'Continue';
    }
  }
}
