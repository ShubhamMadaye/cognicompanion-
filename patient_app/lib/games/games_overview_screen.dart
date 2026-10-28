import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../core/providers/localization_provider.dart';
import 'game_models.dart';
import 'memory_match_game.dart';
import 'sequence_recall_game.dart';
import 'picture_recall_game.dart';
import 'object_recall_game.dart';
import 'word_category_game.dart';
import 'trail_path_game.dart';

class _GameCardData {
  final String id;
  final String titleKey;
  final String descKey;
  final String domain;
  final IconData icon;
  final Color iconColor;
  final Color iconBg;
  final String category; // 'memory', 'attention', 'executive'
  final Widget Function(GameDifficulty difficulty) builder;

  const _GameCardData({
    required this.id,
    required this.titleKey,
    required this.descKey,
    required this.domain,
    required this.icon,
    required this.iconColor,
    required this.iconBg,
    required this.category,
    required this.builder,
  });
}

class GamesOverviewScreen extends StatefulWidget {
  const GamesOverviewScreen({super.key});

  @override
  State<GamesOverviewScreen> createState() => _GamesOverviewScreenState();
}

class _GamesOverviewScreenState extends State<GamesOverviewScreen> {
  String _selectedCategory = 'all';

  // Selected difficulty per game, defaulting to gentle for dignified elderly care
  final Map<String, GameDifficulty> _selectedDifficulties = {
    'memory_match': GameDifficulty.gentle,
    'sequence_recall': GameDifficulty.gentle,
    'picture_recall': GameDifficulty.gentle,
    'object_recall': GameDifficulty.gentle,
    'category_sort': GameDifficulty.gentle,
    'trail_path': GameDifficulty.gentle,
  };

  late final List<_GameCardData> _games = [
    _GameCardData(
      id: 'memory_match',
      titleKey: 'game_memory_match',
      descKey: 'game_memory_match_desc',
      domain: 'Visual Memory',
      icon: Icons.grid_view_rounded,
      iconColor: AppTheme.primaryTealDark,
      iconBg: AppTheme.primaryTealLight,
      category: 'memory',
      builder: (diff) => MemoryMatchGameScreen(difficulty: diff),
    ),
    _GameCardData(
      id: 'sequence_recall',
      titleKey: 'game_sequence_recall',
      descKey: 'game_sequence_recall_desc',
      domain: 'Working Memory',
      icon: Icons.format_list_numbered_rounded,
      iconColor: const Color(0xFFB45309),
      iconBg: const Color(0xFFFEF3C7),
      category: 'attention',
      builder: (diff) => SequenceRecallGameScreen(difficulty: diff),
    ),
    _GameCardData(
      id: 'picture_recall',
      titleKey: 'game_picture_recall',
      descKey: 'game_picture_recall_desc',
      domain: 'Caregiver Recognition',
      icon: Icons.photo_library_outlined,
      iconColor: const Color(0xFF1E3A8A),
      iconBg: const Color(0xFFEFF6FF),
      category: 'memory',
      builder: (diff) => PictureRecallGameScreen(difficulty: diff),
    ),
    _GameCardData(
      id: 'object_recall',
      titleKey: 'game_object_recall',
      descKey: 'game_object_recall_desc',
      domain: 'Short-term Recall',
      icon: Icons.category_outlined,
      iconColor: const Color(0xFF15803D),
      iconBg: const Color(0xFFDCFCE7),
      category: 'memory',
      builder: (diff) => ObjectRecallGameScreen(difficulty: diff),
    ),
    _GameCardData(
      id: 'category_sort',
      titleKey: 'game_category_sort',
      descKey: 'game_category_sort_desc',
      domain: 'Executive Function',
      icon: Icons.sort_rounded,
      iconColor: const Color(0xFF7C3AED),
      iconBg: const Color(0xFFF3E8FF),
      category: 'executive',
      builder: (diff) => WordCategoryGameScreen(difficulty: diff),
    ),
    _GameCardData(
      id: 'trail_path',
      titleKey: 'game_trail_path',
      descKey: 'game_trail_path_desc',
      domain: 'Psychomotor Speed',
      icon: Icons.timeline_rounded,
      iconColor: const Color(0xFF0D9488),
      iconBg: const Color(0xFFCCFBF1),
      category: 'attention',
      builder: (diff) => TrailPathGameScreen(difficulty: diff),
    ),
  ];

  void _launchGame(_GameCardData game) {
    HapticFeedback.lightImpact();
    final currentDiff = _selectedDifficulties[game.id] ?? GameDifficulty.gentle;

    // Show difficulty picker sheet with gentle default
    GameDifficultySheet.show(
      context: context,
      initialDifficulty: currentDiff,
      onDifficultySelected: (chosenDiff) {
        setState(() {
          _selectedDifficulties[game.id] = chosenDiff;
        });
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => game.builder(chosenDiff),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();

    final filteredGames = _games.where((g) {
      if (_selectedCategory == 'all') return true;
      return g.category == _selectedCategory;
    }).toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              Text(
                l.tr('brain_games_title'),
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                l.tr('brain_games_subtitle'),
                style: const TextStyle(
                  fontSize: 14,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 16),

              // Filter Tabs
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildFilterChip('all', 'All Games (${_games.length})'),
                    const SizedBox(width: 8),
                    _buildFilterChip('memory', 'Memory'),
                    const SizedBox(width: 8),
                    _buildFilterChip('attention', 'Attention'),
                    const SizedBox(width: 8),
                    _buildFilterChip('executive', 'Executive'),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Responsive List of Game Cards (eliminates fixed childAspectRatio overflow)
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: filteredGames.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final game = filteredGames[index];
                  final diff = _selectedDifficulties[game.id] ?? GameDifficulty.gentle;

                  return Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.borderSubtle),
                    ),
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Left Icon
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: game.iconBg,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppTheme.borderStone),
                          ),
                          child: Center(
                            child: Icon(game.icon, color: game.iconColor, size: 26),
                          ),
                        ),
                        const SizedBox(width: 14),

                        // Center Info
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: AppTheme.warmSurface,
                                      borderRadius: BorderRadius.circular(4),
                                      border: Border.all(color: AppTheme.borderStone),
                                    ),
                                    child: Text(
                                      game.domain.toUpperCase(),
                                      style: const TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w700,
                                        letterSpacing: 0.4,
                                        color: AppTheme.textSecondary,
                                      ),
                                    ),
                                  ),
                                  const Spacer(),
                                  // Clickable difficulty badge
                                  GestureDetector(
                                    onTap: () => _launchGame(game),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 3,
                                      ),
                                      decoration: BoxDecoration(
                                        color: diff.badgeBgColor,
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(color: diff.badgeBorderColor),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(
                                            diff.label,
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.w700,
                                              color: diff.badgeTextColor,
                                            ),
                                          ),
                                          const SizedBox(width: 2),
                                          Icon(
                                            Icons.tune_rounded,
                                            size: 12,
                                            color: diff.badgeTextColor,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                l.tr(game.titleKey),
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                l.tr(game.descKey),
                                style: const TextStyle(
                                  fontSize: 13,
                                  color: AppTheme.textSecondary,
                                  height: 1.3,
                                ),
                              ),
                              const SizedBox(height: 12),
                              SizedBox(
                                height: 38,
                                width: double.infinity,
                                child: ElevatedButton(
                                  onPressed: () => _launchGame(game),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.primaryTeal,
                                    foregroundColor: Colors.white,
                                    elevation: 0,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Text(
                                        l.tr('play'),
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w700,
                                          fontSize: 14,
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                      const Icon(Icons.play_arrow_rounded, size: 18),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),

              const SizedBox(height: 20),

              // Dignified stats encouragement banner
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: AppTheme.primaryTealDark,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.borderStone),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(
                        Icons.workspace_premium_rounded,
                        color: Colors.white,
                        size: 26,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l.tr('keep_it_up'),
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                              fontSize: 15,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            l.tr('games_encouragement'),
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 13,
                              height: 1.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilterChip(String categoryId, String label) {
    final isSelected = _selectedCategory == categoryId;
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() {
          _selectedCategory = categoryId;
        });
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryTeal : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? AppTheme.primaryTeal : AppTheme.borderSubtle,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            color: isSelected ? Colors.white : AppTheme.textPrimary,
          ),
        ),
      ),
    );
  }
}
