import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';

/// Clinical difficulty levels tailored for cognitive rehabilitation and dementia care.
enum GameDifficulty {
  /// Low frustration, high assistance, larger targets, slower pacing.
  /// Designed for foggy days, early orientation, or low stress.
  gentle,

  /// Balanced cognitive stimulation, standard timing and item count.
  standard,

  /// Enhanced memory span, faster sequences, more items/distractors for deeper engagement.
  focus,
}

extension GameDifficultyExtension on GameDifficulty {
  String get label {
    switch (this) {
      case GameDifficulty.gentle:
        return 'Gentle';
      case GameDifficulty.standard:
        return 'Standard';
      case GameDifficulty.focus:
        return 'Focus';
    }
  }

  String get description {
    switch (this) {
      case GameDifficulty.gentle:
        return 'Relaxed pace with extra guidance and larger targets.';
      case GameDifficulty.standard:
        return 'Balanced everyday memory and concentration exercise.';
      case GameDifficulty.focus:
        return 'Challenging session designed to exercise deeper recall.';
    }
  }

  String get apiValue {
    switch (this) {
      case GameDifficulty.gentle:
        return 'EASY';
      case GameDifficulty.standard:
        return 'MEDIUM';
      case GameDifficulty.focus:
        return 'HARD';
    }
  }

  Color get color {
    switch (this) {
      case GameDifficulty.gentle:
        return const Color(0xFF15803D); // Forest green
      case GameDifficulty.standard:
        return AppTheme.primaryTeal;
      case GameDifficulty.focus:
        return const Color(0xFFB45309); // Warm amber
    }
  }

  Color get bgColor {
    switch (this) {
      case GameDifficulty.gentle:
        return const Color(0xFFDCFCE7);
      case GameDifficulty.standard:
        return AppTheme.primaryTealLight;
      case GameDifficulty.focus:
        return const Color(0xFFFEF3C7);
    }
  }

  Color get badgeBgColor => bgColor;
  Color get badgeBorderColor => color.withValues(alpha: 0.35);
  Color get badgeTextColor => color;

  IconData get icon {
    switch (this) {
      case GameDifficulty.gentle:
        return Icons.spa_outlined;
      case GameDifficulty.standard:
        return Icons.speed_rounded;
      case GameDifficulty.focus:
        return Icons.bolt_rounded;
    }
  }
}

/// A dignified difficulty picker bottom sheet adhering to AGENTS.md design rules.
class GameDifficultySheet extends StatelessWidget {
  final String gameTitle;
  final GameDifficulty currentDifficulty;
  final ValueChanged<GameDifficulty> onSelected;

  const GameDifficultySheet({
    super.key,
    required this.gameTitle,
    required this.currentDifficulty,
    required this.onSelected,
  });

  static Future<GameDifficulty?> show({
    required BuildContext context,
    String gameTitle = 'Brain Game',
    GameDifficulty? current,
    GameDifficulty initialDifficulty = GameDifficulty.gentle,
    ValueChanged<GameDifficulty>? onDifficultySelected,
  }) {
    final effectiveInitial = current ?? initialDifficulty;
    return showModalBottomSheet<GameDifficulty>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => GameDifficultySheet(
        gameTitle: gameTitle,
        currentDifficulty: effectiveInitial,
        onSelected: (diff) {
          Navigator.pop(ctx, diff);
          if (onDifficultySelected != null) {
            onDifficultySelected(diff);
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.85,
      ),
      child: SingleChildScrollView(
        physics: const ClampingScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(22, 16, 22, 28),
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
            const SizedBox(height: 18),
            const Text(
              'Select Difficulty',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                letterSpacing: -0.2,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Tailored for $gameTitle',
              style: const TextStyle(
                fontSize: 13,
                color: AppTheme.textSecondary,
              ),
            ),
            const SizedBox(height: 18),
            ...GameDifficulty.values.map((diff) {
              final isSelected = diff == currentDifficulty;
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InkWell(
                  onTap: () {
                    HapticFeedback.selectionClick();
                    onSelected(diff);
                  },
                  borderRadius: BorderRadius.circular(14),
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: isSelected ? diff.bgColor.withValues(alpha: 0.5) : Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isSelected ? diff.color : AppTheme.borderSubtle,
                        width: isSelected ? 1.8 : 1.0,
                      ),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: diff.bgColor,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(diff.icon, color: diff.color, size: 22),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    diff.label,
                                    style: TextStyle(
                                      fontSize: 15,
                                      fontWeight: FontWeight.w700,
                                      color: isSelected ? diff.color : AppTheme.textPrimary,
                                    ),
                                  ),
                                  if (isSelected) ...[
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: diff.color,
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: const Text(
                                        'Active',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 10,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                              const SizedBox(height: 3),
                              Text(
                                diff.description,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.textSecondary,
                                  height: 1.3,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Icon(
                          isSelected ? Icons.check_circle_rounded : Icons.circle_outlined,
                          color: isSelected ? diff.color : Colors.grey.shade400,
                          size: 22,
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
