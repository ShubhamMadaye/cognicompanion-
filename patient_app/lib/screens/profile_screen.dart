import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/auth_provider.dart';
import '../core/providers/patient_provider.dart';
import '../core/providers/localization_provider.dart';
import '../core/providers/accessibility_provider.dart';
import '../core/localization/app_localizations.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Future<void> _callEmergency(BuildContext context, String phone) async {
    final cleanPhone = phone.replaceAll(RegExp(r'[\s\-()]'), '');
    final uri = Uri(scheme: 'tel', path: cleanPhone);
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      } else {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Cannot launch phone dialer for $cleanPhone')),
        );
      }
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Dialer error: $e')),
      );
    }
  }

  /// Opens the emergency contact modal with options to Call or Edit.
  void _showEmergencyContactDialog(BuildContext context, PatientProvider provider) {
    final nameCtrl = TextEditingController(text: provider.profile.emergencyName);
    final phoneCtrl = TextEditingController(text: provider.profile.emergencyPhone);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(ctx).size.height * 0.88,
        ),
        child: SingleChildScrollView(
          physics: const ClampingScrollPhysics(),
          padding: EdgeInsets.only(
            left: 24,
            right: 24,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Row(
                children: [
                  Icon(Icons.contact_phone_rounded, color: AppTheme.gentleRose, size: 24),
                  SizedBox(width: 10),
                  Text(
                    'Emergency Caregiver Contact',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextField(
                controller: nameCtrl,
                decoration: InputDecoration(
                  labelText: 'Caregiver / Contact Name',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  prefixIcon: const Icon(Icons.person_rounded),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: phoneCtrl,
                keyboardType: TextInputType.phone,
                decoration: InputDecoration(
                  labelText: 'Phone Number',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  prefixIcon: const Icon(Icons.phone_rounded),
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        Navigator.pop(ctx);
                        _callEmergency(context, provider.profile.emergencyPhone);
                      },
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.gentleRose,
                        side: const BorderSide(color: AppTheme.gentleRose),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      icon: const Icon(Icons.call_rounded),
                      label: const Text('Call Now'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        final newName = nameCtrl.text.trim();
                        final newPhone = phoneCtrl.text.trim();
                        if (newName.isNotEmpty && newPhone.isNotEmpty) {
                          provider.updateEmergencyContact(name: newName, phone: newPhone);
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Emergency contact saved')),
                          );
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryTeal,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      icon: const Icon(Icons.check_rounded),
                      label: const Text('Save'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Opens the Text Size Picker bottom sheet.
  void _showTextSizePicker(BuildContext context, AccessibilityProvider a) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(ctx).size.height * 0.88,
        ),
        child: SingleChildScrollView(
          physics: const ClampingScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Display Text Size',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
              ),
              const SizedBox(height: 6),
              const Text(
                'Enlarge text across the app for easier reading and comfortable viewing.',
                style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 16),
              _textSizeRadioTile(
                title: 'Default (100%)',
                subtitle: 'Recommended for standard screens',
                sampleSize: 14,
                selected: a.textScaleLevel == TextScaleLevel.normal,
                onTap: () {
                  a.setTextScaleLevel(TextScaleLevel.normal);
                  Navigator.pop(ctx);
                },
              ),
              _textSizeRadioTile(
                title: 'Large (118%)',
                subtitle: 'Comfortable reading for everyday dementia care',
                sampleSize: 16.5,
                selected: a.textScaleLevel == TextScaleLevel.large,
                onTap: () {
                  a.setTextScaleLevel(TextScaleLevel.large);
                  Navigator.pop(ctx);
                },
              ),
              _textSizeRadioTile(
                title: 'Extra Large (135%)',
                subtitle: 'Maximum visibility with large touch targets',
                sampleSize: 19,
                selected: a.textScaleLevel == TextScaleLevel.extraLarge,
                onTap: () {
                  a.setTextScaleLevel(TextScaleLevel.extraLarge);
                  Navigator.pop(ctx);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _textSizeRadioTile({
    required String title,
    required String subtitle,
    required double sampleSize,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: selected ? AppTheme.primaryTeal.withValues(alpha: 0.08) : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: selected ? AppTheme.primaryTeal : Colors.grey.shade300,
          width: selected ? 1.8 : 1,
        ),
      ),
      child: ListTile(
        onTap: onTap,
        title: Text(
          title,
          style: TextStyle(
            fontSize: sampleSize,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
            color: selected ? AppTheme.primaryTealDark : AppTheme.textPrimary,
          ),
        ),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
        trailing: selected
            ? const Icon(Icons.check_circle_rounded, color: AppTheme.primaryTeal)
            : const Icon(Icons.circle_outlined, color: Colors.grey),
      ),
    );
  }

  /// Opens the Accessibility Settings sheet.
  void _showAccessibilitySheet(BuildContext context, AccessibilityProvider a) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocalState) => ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(ctx).size.height * 0.88,
          ),
          child: SingleChildScrollView(
            physics: const ClampingScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Row(
                  children: [
                    Icon(Icons.accessibility_new_rounded, color: AppTheme.softOrange, size: 24),
                    SizedBox(width: 10),
                    Text(
                      'Accessibility & Voice Settings',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SwitchListTile(
                  title: const Text('High Contrast Mode', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Sharper text borders and deep black typography for low vision'),
                  value: a.isHighContrast,
                  activeThumbColor: AppTheme.primaryTeal,
                  onChanged: (val) {
                    a.setHighContrast(val);
                    setLocalState(() {});
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  title: const Text('Haptic Touch Feedback', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Subtle vibration feedback when interacting with cards and voice'),
                  value: a.hapticEnabled,
                  activeThumbColor: AppTheme.primaryTeal,
                  onChanged: (val) {
                    a.setHapticEnabled(val);
                    setLocalState(() {});
                  },
                ),
                const Divider(height: 1),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Assistant Voice Speed', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                          Text(
                            '${(a.voiceSpeakingRate * 200).toInt()}% speed',
                            style: const TextStyle(fontWeight: FontWeight.w700, color: AppTheme.primaryTeal),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Slower speech allows older adults to absorb memory prompts with ease.',
                        style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                      ),
                      Slider(
                        value: a.voiceSpeakingRate,
                        min: 0.35,
                        max: 0.70,
                        divisions: 7,
                        label: '${(a.voiceSpeakingRate * 200).toInt()}%',
                        activeColor: AppTheme.primaryTeal,
                        onChanged: (val) {
                          a.setVoiceSpeakingRate(val);
                          setLocalState(() {});
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Opens the Notifications Preference bottom sheet.
  void _showNotificationSettingsSheet(BuildContext context, AccessibilityProvider a) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocalState) => ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(ctx).size.height * 0.88,
          ),
          child: SingleChildScrollView(
            physics: const ClampingScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Row(
                  children: [
                    Icon(Icons.notifications_active_rounded, color: AppTheme.warmAmber, size: 24),
                    SizedBox(width: 10),
                    Text(
                      'Notification & Alert Preferences',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SwitchListTile(
                  title: const Text('Medication Schedule Reminders', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Gentle voice & chime alerts when prescription doses are due'),
                  value: a.notifyMedication,
                  activeThumbColor: AppTheme.warmAmber,
                  onChanged: (val) {
                    a.setNotificationPref(medication: val);
                    setLocalState(() {});
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  title: const Text('Daily Routine & Meal Prompts', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Prompts for morning walks, afternoon tea, and family calls'),
                  value: a.notifyRoutine,
                  activeThumbColor: AppTheme.warmAmber,
                  onChanged: (val) {
                    a.setNotificationPref(routine: val);
                    setLocalState(() {});
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  title: const Text('Compassionate Memory Check-ins', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Periodic friendly memory games and photo recall sessions'),
                  value: a.notifyCheckins,
                  activeThumbColor: AppTheme.warmAmber,
                  onChanged: (val) {
                    a.setNotificationPref(checkins: val);
                    setLocalState(() {});
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }



  /// Opens the language picker bottom sheet.
  void _showLanguagePicker(BuildContext context, LocalizationProvider l) async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _LanguagePickerSheet(currentLocale: l.locale),
    );
    if (selected != null && mounted) {
      // ignore: use_build_context_synchronously
      context.read<LocalizationProvider>().setLocale(selected);
    }
  }

  void _confirmSignOut(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Sign Out', style: TextStyle(fontWeight: FontWeight.w700)),
        content: const Text(
          'Are you sure you want to sign out? You will be returned to the login screen.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel', style: TextStyle(color: AppTheme.textSecondary)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.gentleRose,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () async {
              Navigator.pop(ctx);
              context.read<PatientProvider>().reset();
              await context.read<AuthProvider>().logout();
            },
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    final accessibility = context.watch<AccessibilityProvider>();

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Consumer<PatientProvider>(builder: (context, provider, _) {
          final profile = provider.profile;
          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              children: [
                const SizedBox(height: 8),
                // ── Avatar & Name Card ───────────────────────────────────────
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 68,
                        height: 68,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppTheme.primaryTeal,
                          border: Border.all(color: AppTheme.borderStone, width: 2),
                        ),
                        child: Center(
                          child: Text(
                            profile.firstName.isNotEmpty ? profile.firstName[0] : 'P',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              profile.fullName,
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: AppTheme.primaryTealLight,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                '${l.localeName} • Patient Profile',
                                style: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.primaryTealDark,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // ── Settings List ───────────────────────────────────────────
                Container(
                  decoration: AppTheme.cardDecoration,
                  child: Column(
                    children: [
                      // Language row
                      _settingRow(
                        icon: Icons.language_rounded,
                        iconColor: AppTheme.primaryTeal,
                        title: l.tr('language'),
                        value: l.localeName,
                        onTap: () => _showLanguagePicker(context, l),
                      ),
                      _divider(),
                      // Text Size
                      _settingRow(
                        icon: Icons.text_fields_rounded,
                        iconColor: AppTheme.softBlue,
                        title: l.tr('text_size'),
                        value: accessibility.textScaleLabel,
                        onTap: () => _showTextSizePicker(context, accessibility),
                      ),
                      _divider(),
                      // Accessibility Sheet
                      _settingRow(
                        icon: Icons.accessibility_new_rounded,
                        iconColor: AppTheme.softOrange,
                        title: l.tr('accessibility'),
                        value: accessibility.isHighContrast ? 'High Contrast' : 'Standard',
                        onTap: () => _showAccessibilitySheet(context, accessibility),
                      ),
                      _divider(),
                      // Simple Mode toggle
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        child: Row(
                          children: [
                            Container(
                              width: 42,
                              height: 42,
                              decoration: BoxDecoration(
                                color: AppTheme.gentleGreen.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(Icons.wb_sunny_rounded, color: AppTheme.gentleGreen, size: 22),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    l.tr('simple_mode'),
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                      color: AppTheme.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    l.tr('simple_mode_desc'),
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: AppTheme.textSecondary,
                                      height: 1.3,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Switch(
                              value: accessibility.isSimpleMode,
                              onChanged: (v) => accessibility.setSimpleMode(v),
                              thumbColor: WidgetStateProperty.resolveWith(
                                (states) => states.contains(WidgetState.selected) ? Colors.white : Colors.grey,
                              ),
                              trackColor: WidgetStateProperty.resolveWith(
                                (states) => states.contains(WidgetState.selected)
                                    ? AppTheme.primaryTeal
                                    : Colors.grey.shade300,
                              ),
                            ),
                          ],
                        ),
                      ),
                      _divider(),
                      // Emergency Contact
                      GestureDetector(
                        onTap: () => _showEmergencyContactDialog(context, provider),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          child: Row(
                            children: [
                              Container(
                                width: 42,
                                height: 42,
                                decoration: BoxDecoration(
                                  color: AppTheme.gentleRose.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(Icons.phone_rounded, color: AppTheme.gentleRose, size: 22),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      l.tr('emergency_contact'),
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.textPrimary,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${profile.emergencyName} • ${profile.emergencyPhone}',
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: AppTheme.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const Icon(Icons.chevron_right, color: AppTheme.textSecondary),
                            ],
                          ),
                        ),
                      ),
                      _divider(),
                      // Notifications
                      _settingRow(
                        icon: Icons.notifications_rounded,
                        iconColor: AppTheme.warmAmber,
                        title: l.tr('notifications'),
                        value: 'Alerts Active',
                        onTap: () => _showNotificationSettingsSheet(context, accessibility),
                      ),

                      _divider(),
                      // Sign Out
                      _settingRow(
                        icon: Icons.logout_rounded,
                        iconColor: AppTheme.gentleRose,
                        title: 'Sign Out / Switch Patient',
                        value: '',
                        onTap: () => _confirmSignOut(context),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // ── App Brand Footer ─────────────────────────────────────────
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: Image.asset(
                        'assets/images/app_logo.png',
                        width: 20,
                        height: 20,
                        fit: BoxFit.contain,
                        errorBuilder: (_, __, ___) => Image.asset(
                          'assets/images/logo1.png',
                          width: 20,
                          height: 20,
                          errorBuilder: (_, __, ___) => Image.asset(
                            'assets/images/mainlogo.png',
                            width: 20,
                            height: 20,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      l.tr('version_label'),
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textLight,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
              ],
            ),
          );
        }),
      ),
    );
  }

  Widget _settingRow({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String value,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: iconColor, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),
            if (value.isNotEmpty)
              Flexible(
                child: Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                ),
              ),
            const SizedBox(width: 6),
            const Icon(Icons.chevron_right, color: AppTheme.textSecondary),
          ],
        ),
      ),
    );
  }

  Widget _divider() => const Divider(height: 1, indent: 72, endIndent: 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// Language Picker — DraggableScrollableSheet (scrollable, overflow-safe)
// ─────────────────────────────────────────────────────────────────────────────

typedef _PickerItem = Map<String, dynamic>;

class _LanguagePickerSheet extends StatelessWidget {
  final String currentLocale;
  const _LanguagePickerSheet({required this.currentLocale});

  List<_PickerItem> _buildItems() {
    const locales = AppLocalizations.supportedLocales;
    const mainCodes = ['en', 'hi', 'mr', 'bn', 'ta', 'te', 'kn', 'gu', 'pa', 'ml'];
    const neCodes = ['as', 'brx', 'mni', 'lus', 'kha', 'ne'];

    final items = <_PickerItem>[];

    items.add({'type': 'header', 'label': 'India — Official Languages'});
    for (final l in locales.where((l) => mainCodes.contains(l['code']))) {
      items.add({'type': 'locale', ...l});
    }

    items.add({'type': 'header', 'label': 'North East India'});
    for (final l in locales.where((l) => neCodes.contains(l['code']))) {
      items.add({'type': 'locale', ...l});
    }

    return items;
  }

  @override
  Widget build(BuildContext context) {
    final title = context.read<LocalizationProvider>().tr('select_language');
    final items = _buildItems();

    return DraggableScrollableSheet(
      initialChildSize: 0.70,
      minChildSize: 0.40,
      maxChildSize: 0.95,
      expand: false,
      snap: true,
      snapSizes: const [0.55, 0.70, 0.95],
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.only(top: 12, bottom: 4),
                child: Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
              Expanded(
                child: ListView.builder(
                  controller: scrollController,
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    if (item['type'] == 'header') {
                      return Padding(
                        padding: const EdgeInsets.fromLTRB(20, 16, 20, 6),
                        child: Text(
                          item['label'] as String,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      );
                    }

                    final code = item['code'] as String;
                    final name = item['name'] as String;
                    final nativeName = item['nativeName'] as String;
                    final isSelected = code == currentLocale;

                    return ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 2),
                      leading: Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          color: isSelected
                              ? AppTheme.primaryTeal.withValues(alpha: 0.15)
                              : Colors.grey.shade100,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Center(
                          child: Text(
                            code.toUpperCase(),
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: isSelected ? AppTheme.primaryTeal : AppTheme.textSecondary,
                            ),
                          ),
                        ),
                      ),
                      title: Text(
                        nativeName,
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                          color: isSelected ? AppTheme.primaryTealDark : AppTheme.textPrimary,
                        ),
                      ),
                      subtitle: Text(name, style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                      trailing: isSelected
                          ? const Icon(Icons.check_circle_rounded, color: AppTheme.primaryTeal)
                          : null,
                      onTap: () => Navigator.pop(context, code),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
