import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/patient_provider.dart';
import '../core/providers/localization_provider.dart';
import '../models/models.dart';
import 'voice_chat_screen.dart';
import 'today_screen.dart';
import 'memories_screen.dart';
import 'people_screen.dart';
import '../games/games_overview_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Future<void> _callEmergency(BuildContext context) async {
    final phone = context.read<PatientProvider>().profile.emergencyPhone;
    final uri = Uri(scheme: 'tel', path: phone);
    try {
      if (await canLaunchUrl(uri)) await launchUrl(uri);
    } catch (_) {
      if (context.mounted) {
        final l = context.read<LocalizationProvider>();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l.tr('unable_to_call'))),
        );
      }
    }
  }

  String _greeting(LocalizationProvider l) {
    final hour = DateTime.now().hour;
    if (hour < 12) return l.tr('greeting_morning');
    if (hour < 17) return l.tr('greeting_afternoon');
    return l.tr('greeting_evening');
  }

  String _formattedDate() {
    return DateFormat('EEEE, MMMM d').format(DateTime.now());
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Consumer<PatientProvider>(
          builder: (context, provider, _) {
            final profile = provider.profile;
            final todayItems = provider.todayTimeline;
            return RefreshIndicator(
              color: AppTheme.primaryTeal,
              onRefresh: () async {
                HapticFeedback.lightImpact();
                await provider.loadTodayTimeline(silent: true);
              },
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                  // ── Top Brand Bar & Emergency Quick Contact ───────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 34,
                            height: 34,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppTheme.borderStone),
                            ),
                            padding: const EdgeInsets.all(4),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(6),
                              child: Image.asset(
                                'assets/images/app_logo.png',
                                fit: BoxFit.contain,
                                errorBuilder: (_, __, ___) => const Icon(
                                  Icons.favorite_rounded,
                                  size: 18,
                                  color: AppTheme.primaryTeal,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          const Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'CogniCompanion',
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: -0.2,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              Text(
                                'Daily Memory & Care',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          GestureDetector(
                            onTap: () async {
                              HapticFeedback.lightImpact();
                              await provider.loadTodayTimeline(silent: true);
                            },
                            child: Container(
                              padding: const EdgeInsets.all(7),
                              margin: const EdgeInsets.only(right: 8),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFFE2DDD5)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    decoration: const BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: Color(0xFF15803D), // Green live indicator
                                    ),
                                  ),
                                  const SizedBox(width: 5),
                                  const Text(
                                    'Live',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFF15803D),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          GestureDetector(
                            onTap: () => _callEmergency(context),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 11, vertical: 7),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFFE2DDD5)),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withValues(alpha: 0.02),
                                    blurRadius: 4,
                                    offset: const Offset(0, 1),
                                  ),
                                ],
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.phone_in_talk_rounded,
                                      color: AppTheme.primaryTeal, size: 14),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Call ${profile.emergencyFirstName}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      color: AppTheme.primaryTeal,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // ── Patient Identity Hero Banner (Dignified & Reassuring) ─
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: AppTheme.borderStone, width: 1),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.02),
                          blurRadius: 6,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _greeting(l),
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.textSecondary,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                profile.firstName,
                                style: const TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.w800,
                                  color: AppTheme.textPrimary,
                                  letterSpacing: -0.3,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '78 years · Hindi & English · Care Circle Active',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey.shade600,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF7F5F0),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.calendar_today_outlined,
                                        size: 11, color: AppTheme.textSecondary),
                                    const SizedBox(width: 5),
                                    Text(
                                      _formattedDate(),
                                      style: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.textPrimary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          width: 52,
                          height: 52,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: const Color(0xFFF2EFE9),
                            border: Border.all(
                                color: const Color(0xFFE2DDD5), width: 1.5),
                          ),
                          child: Center(
                            child: Text(
                              profile.firstName.isNotEmpty
                                  ? profile.firstName.substring(0, 1).toUpperCase()
                                  : 'S',
                              style: const TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.primaryTeal,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // ── Hero Voice Interaction Card ("The Tactile Instrument") ─
                  GestureDetector(
                    onTap: () {
                      HapticFeedback.lightImpact();
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const VoiceChatScreen()),
                      );
                    },
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: const Color(0xFF134E5A), // Deep Slate Teal
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                            color: const Color(0xFF1D5D6B), width: 1.2),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.08),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Status line
                          Row(
                            children: [
                              Container(
                                width: 7,
                                height: 7,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: Color(0xFF34D399), // Subtle active emerald
                                ),
                              ),
                              const SizedBox(width: 7),
                              const Text(
                                'VOICE COMPANION · READY TO TALK',
                                style: TextStyle(
                                  color: Colors.white70,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.8,
                                ),
                              ),
                              const Spacer(),
                              const Icon(Icons.graphic_eq_rounded,
                                  size: 16, color: Colors.white70),
                            ],
                          ),
                          const SizedBox(height: 14),
                          Row(
                            children: [
                              // Tactile Cream Mic Button
                              Container(
                                width: 56,
                                height: 56,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: const Color(0xFFFAF8F5),
                                  border: Border.all(
                                      color: const Color(0xFFE8E4DC), width: 1.5),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(alpha: 0.12),
                                      blurRadius: 8,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                                child: const Icon(
                                  Icons.mic_rounded,
                                  color: Color(0xFF134E5A),
                                  size: 30,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Tap to Talk with Companion',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 17,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: -0.2,
                                      ),
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      'Ask about your day, memories, or next medicine',
                                      style: TextStyle(
                                        color: Colors.white.withValues(alpha: 0.82),
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500,
                                        height: 1.3,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const Icon(
                                Icons.arrow_forward_ios_rounded,
                                color: Colors.white54,
                                size: 16,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // ── "Next Up on Schedule" Spotlight (Caregiver Sync Feature)
                  _buildNextUpSpotlight(context, provider),
                  const SizedBox(height: 14),

                  // ── 3 Care Pillars (Memories, Brain Play, Family) ──────────
                  _buildCarePillars(context, l),
                  const SizedBox(height: 16),

                  // ── Today's Plan (Chronological Timeline) ─────────────────
                  _buildTodayPlanCard(context, todayItems, provider, l),
                  const SizedBox(height: 14),
                ],
              ),
            ),
          );
        },
      ),
    ),
  );
}

  /// Spotlight card mirroring the dashboard's Next Up on Schedule
  Widget _buildNextUpSpotlight(BuildContext context, PatientProvider provider) {
    final pendingItems = provider.todayTimeline.where((i) => !i.isCompleted).toList();
    if (pendingItems.isEmpty) {
      return const SizedBox.shrink();
    }
    final nextItem = pendingItems.first;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderStone),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7), // Warm amber tint
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'NEXT UP ON SCHEDULE · ${nextItem.timeStr.toUpperCase()}',
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.6,
                    color: Color(0xFFB45309),
                  ),
                ),
              ),
              Text(
                nextItem.isMedication ? 'Prescription' : 'Daily Routine',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            nextItem.title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: AppTheme.textPrimary,
            ),
          ),
          if (nextItem.subtitle.isNotEmpty) ...[
            const SizedBox(height: 3),
            Text(
              nextItem.subtitle,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// 3 Core Pillars: Memories, Brain Games, Family Circle
  Widget _buildCarePillars(BuildContext context, LocalizationProvider l) {
    return Row(
      children: [
        // 1. Memories
        Expanded(
          child: _pillarCard(
            context,
            icon: Icons.photo_library_outlined,
            title: 'Memories',
            subtitle: 'Past Days',
            accentColor: const Color(0xFFB45309), // Warm Amber
            bgColor: const Color(0xFFFEFBF6),
            onTap: () {
              HapticFeedback.lightImpact();
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const MemoriesScreen()),
              );
            },
          ),
        ),
        const SizedBox(width: 10),

        // 2. Brain Play
        Expanded(
          child: _pillarCard(
            context,
            icon: Icons.psychology_outlined,
            title: 'Brain Play',
            subtitle: 'Word Games',
            accentColor: AppTheme.primaryTeal,
            bgColor: const Color(0xFFF5F9FA),
            onTap: () {
              HapticFeedback.lightImpact();
              Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) => const GamesOverviewScreen()),
              );
            },
          ),
        ),
        const SizedBox(width: 10),

        // 3. Family
        Expanded(
          child: _pillarCard(
            context,
            icon: Icons.people_outline_rounded,
            title: 'Family',
            subtitle: 'Care Circle',
            accentColor: const Color(0xFF15803D), // Emerald
            bgColor: const Color(0xFFF5FAF6),
            onTap: () {
              HapticFeedback.lightImpact();
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const PeopleScreen()),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _pillarCard(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accentColor,
    required Color bgColor,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.borderStone, width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.02),
              blurRadius: 4,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: Column(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: accentColor.withValues(alpha: 0.25)),
              ),
              child: Center(
                child: Icon(icon, color: accentColor, size: 20),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              title,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: const TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTodayPlanCard(BuildContext context,
      List<TodayTimelineItem> items, PatientProvider provider, LocalizationProvider l) {
    final displayItems = items.take(4).toList();
    final completedCount = displayItems.where((i) => i.isCompleted).length;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderStone),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "TODAY'S CARE SCHEDULE",
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.8,
                      color: AppTheme.primaryTeal,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    displayItems.isNotEmpty
                        ? '$completedCount of ${displayItems.length} completed'
                        : 'No pending items',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
              GestureDetector(
                onTap: () {
                  HapticFeedback.selectionClick();
                  Navigator.push(context,
                      MaterialPageRoute(builder: (_) => const TodayScreen()));
                },
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF7F5F0),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFE8E4DC)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Full Plan',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppTheme.primaryTeal,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      SizedBox(width: 4),
                      Icon(Icons.arrow_forward_ios_rounded,
                          size: 10, color: AppTheme.primaryTeal),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          if (displayItems.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Center(
                child: Text(
                  l.tr('no_plans_today'),
                  style: AppTheme.secondaryText,
                ),
              ),
            )
          else
            ...displayItems.map((item) => _buildPlanRow(item, provider, l)),
        ],
      ),
    );
  }

  Widget _buildPlanRow(
      TodayTimelineItem item, PatientProvider provider, LocalizationProvider l) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        decoration: BoxDecoration(
          color: item.isCompleted ? const Color(0xFFFAF9F6) : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: item.isCompleted
                ? const Color(0xFFE2DDD5)
                : const Color(0xFFE8E4DC),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            // Checkmark button with accessible 34px touch target
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: item.isMedication
                  ? () {
                      HapticFeedback.lightImpact();
                      provider.toggleItemCompleted(item.id);
                    }
                  : null,
              child: Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: item.isCompleted
                      ? AppTheme.gentleGreen
                      : Colors.white,
                  border: Border.all(
                    color: item.isCompleted
                        ? AppTheme.gentleGreen
                        : const Color(0xFFCBC6BC),
                    width: 2,
                  ),
                ),
                child: item.isCompleted
                    ? const Icon(Icons.check_rounded, color: Colors.white, size: 18)
                    : null,
              ),
            ),
            const SizedBox(width: 12),

            // Time badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFFF2EFE9),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                item.timeStr,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                  fontFamily: 'monospace',
                ),
              ),
            ),
            const SizedBox(width: 10),

            // Title & Details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: item.isCompleted
                          ? AppTheme.textSecondary
                          : AppTheme.textPrimary,
                      decoration:
                          item.isCompleted ? TextDecoration.lineThrough : null,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (item.subtitle.isNotEmpty) ...[
                    const SizedBox(height: 1),
                    Text(
                      item.subtitle,
                      style: AppTheme.secondaryText.copyWith(fontSize: 11),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),

            // Action / Status Pill
            if (item.isMedication)
              Padding(
                padding: const EdgeInsets.only(left: 6),
                child: item.isCompleted
                    ? Text(
                        item.takenAt != null ? '✓ ${item.takenAt}' : '✓ Recorded',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.gentleGreen,
                        ),
                      )
                    : GestureDetector(
                        onTap: () {
                          HapticFeedback.lightImpact();
                          provider.toggleItemCompleted(item.id);
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 9, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryTeal,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'Take Dose',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                              fontSize: 11,
                            ),
                          ),
                        ),
                      ),
              ),
          ],
        ),
      ),
    );
  }
}
