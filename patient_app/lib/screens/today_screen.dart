import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/patient_provider.dart';
import '../core/providers/localization_provider.dart';
import '../models/models.dart';

class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key});

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<PatientProvider>().loadTodayTimeline();
    });
  }

  String _formattedDate() {
    final now = DateTime.now();
    const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return '${weekdays[now.weekday - 1]}, ${now.day} ${months[now.month - 1]}';
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        leading: Navigator.canPop(context)
            ? IconButton(
                icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppTheme.textPrimary),
                onPressed: () => Navigator.pop(context),
              )
            : null,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l.tr('today_daily_plan'),
                style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.5,
                    color: AppTheme.textPrimary)),
            Text(_formattedDate(),
                style: const TextStyle(
                    fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w500)),
          ],
        ),
        elevation: 0,
      ),
      body: Consumer<PatientProvider>(
        builder: (context, provider, _) {
          if (provider.isLoadingTimeline) {
            return const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryTeal),
            );
          }

          final items = provider.todayTimeline.isNotEmpty
              ? provider.todayTimeline
              : TodayTimelineItem.mockItems();

          return RefreshIndicator(
            color: AppTheme.primaryTeal,
            onRefresh: () => provider.loadTodayTimeline(),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: _countWithHeaders(items),
              itemBuilder: (context, index) {
                return _buildRow(context, index, items, provider, l);
              },
            ),
          );
        },
      ),
    );
  }

  int _countWithHeaders(List<TodayTimelineItem> items) {
    final periods = <String>[];
    for (final item in items) {
      final p = _timePeriodKey(item.timeStr);
      if (periods.isEmpty || periods.last != p) periods.add(p);
    }
    return items.length + periods.length;
  }

  Widget _buildRow(BuildContext context, int flatIndex,
      List<TodayTimelineItem> items, PatientProvider provider, LocalizationProvider l) {
    int pos = 0;
    String? lastPeriod;
    for (int i = 0; i < items.length; i++) {
      final period = _timePeriodKey(items[i].timeStr);
      if (period != lastPeriod) {
        if (pos == flatIndex) return _buildSectionHeader(l.tr(period));
        lastPeriod = period;
        pos++;
      }
      if (pos == flatIndex) return _buildTimelineRow(items[i], provider, l);
      pos++;
    }
    return const SizedBox.shrink();
  }

  Widget _buildSectionHeader(String period) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
      child: Text(
        period.toUpperCase(),
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.0,
          color: AppTheme.primaryTeal,
        ),
      ),
    );
  }

  Widget _buildTimelineRow(TodayTimelineItem item, PatientProvider provider, LocalizationProvider l) {
    final iconData = _iconFor(item);
    final iconBg = _iconBgFor(item);
    final iconColor = _iconColorFor(item);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
      child: Container(
        decoration: BoxDecoration(
          color: item.isCompleted ? const Color(0xFFF7F5F0) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: item.isCompleted ? const Color(0xFFE2DDD5) : AppTheme.borderSubtle,
            width: 1.0,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.02),
              blurRadius: 4,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            // Accessible Tap Target for Completion Checkbox
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: item.isMedication
                  ? () {
                      HapticFeedback.lightImpact();
                      provider.toggleItemCompleted(item.id);
                    }
                  : null,
              child: Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: item.isCompleted ? AppTheme.gentleGreen : Colors.white,
                  border: Border.all(
                    color: item.isCompleted ? AppTheme.gentleGreen : const Color(0xFFCBC6BC),
                    width: 2,
                  ),
                ),
                child: item.isCompleted
                    ? const Icon(Icons.check_rounded, color: Colors.white, size: 20)
                    : null,
              ),
            ),
            const SizedBox(width: 14),

            // Semantic Icon Container (No emojis, no rainbow pastels)
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: const Color(0xFFE8E4DC),
                  width: 0.8,
                ),
              ),
              child: Center(
                child: Icon(iconData, color: iconColor, size: 20),
              ),
            ),
            const SizedBox(width: 14),

            // Title and Details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: item.isCompleted
                          ? AppTheme.textSecondary
                          : AppTheme.textPrimary,
                      decoration:
                          item.isCompleted ? TextDecoration.lineThrough : null,
                    ),
                  ),
                  if (item.subtitle.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      item.subtitle,
                      style: AppTheme.secondaryText.copyWith(fontSize: 12),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),

            // Time & Action Status
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF2EFE9),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      item.timeStr,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ),
                  if (item.isMedication) ...[
                    const SizedBox(height: 6),
                    if (item.isCompleted)
                      Text(
                        item.takenAt != null ? '✓ ${item.takenAt}' : '✓ Recorded',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.gentleGreen,
                        ),
                      )
                    else
                      GestureDetector(
                        onTap: () {
                          HapticFeedback.lightImpact();
                          provider.toggleItemCompleted(item.id);
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryTeal,
                            borderRadius: BorderRadius.circular(8),
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
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _iconFor(TodayTimelineItem item) {
    if (item.isMedication) return Icons.medication_outlined;
    final titleLower = item.title.toLowerCase();
    if (titleLower.contains('breakfast') || titleLower.contains('lunch') || titleLower.contains('dinner')) {
      return Icons.restaurant_outlined;
    }
    if (titleLower.contains('tea') || titleLower.contains('snack')) {
      return Icons.local_cafe_outlined;
    }
    if (item.kind == 'game') {
      return Icons.psychology_outlined;
    }
    if (titleLower.contains('walk') || titleLower.contains('exercise')) {
      return Icons.directions_walk_rounded;
    }
    return Icons.schedule_rounded;
  }

  Color _iconBgFor(TodayTimelineItem item) {
    if (item.isMedication) return const Color(0xFFF0F6F7);
    if (item.kind == 'game') return const Color(0xFFF7F5F0);
    return const Color(0xFFF4F3EE);
  }

  Color _iconColorFor(TodayTimelineItem item) {
    if (item.isMedication) return AppTheme.primaryTeal;
    if (item.kind == 'game') return const Color(0xFF8B5E3C);
    return AppTheme.textPrimary;
  }

  /// Returns translation key (not the translated string) for the period.
  String _timePeriodKey(String timeStr) {
    try {
      final upper = timeStr.toUpperCase();
      if (upper.contains('AM')) {
        final hour = int.tryParse(timeStr.split(':')[0].trim()) ?? 0;
        if (hour < 12) return 'morning';
      }
      if (upper.contains('PM')) {
        final hour = int.tryParse(timeStr.split(':')[0].trim()) ?? 12;
        if (hour == 12 || hour < 5) return 'afternoon';
        return 'evening';
      }
    } catch (_) {}
    return 'today';
  }
}
