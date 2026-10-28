import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import 'game_models.dart';
import 'game_result_screen.dart';

class WordCategoryGameScreen extends StatefulWidget {
  final GameDifficulty difficulty;

  const WordCategoryGameScreen({
    super.key,
    this.difficulty = GameDifficulty.gentle,
  });

  @override
  State<WordCategoryGameScreen> createState() => _WordCategoryGameScreenState();
}

class _CategoryChallenge {
  final String category;
  final String description;
  final List<String> targetItems;
  final List<String> distractorItems;

  const _CategoryChallenge({
    required this.category,
    required this.description,
    required this.targetItems,
    required this.distractorItems,
  });
}

class _WordCategoryGameScreenState extends State<WordCategoryGameScreen> {
  late Stopwatch _stopwatch;
  int _currentRound = 0;
  int _totalRounds = 1;
  int _score = 0;
  int _totalCorrect = 0;
  int _totalMistakes = 0;

  final List<_CategoryChallenge> _challenges = const [
    _CategoryChallenge(
      category: 'Kitchen Essentials',
      description: 'Select everything typically found in a kitchen',
      targetItems: ['Teaspoon', 'Frying Pan', 'Kettle', 'Plate', 'Blender'],
      distractorItems: ['Pillow', 'Toothbrush', 'Umbrella', 'Comb', 'Hammer'],
    ),
    _CategoryChallenge(
      category: 'Clothing & Wearables',
      description: 'Select items that you can wear',
      targetItems: ['Cardigan', 'Woolen Socks', 'Scarf', 'Slippers', 'Cap'],
      distractorItems: ['Notebook', 'Telephone', 'Clock', 'Flowerpot', 'Lamp'],
    ),
    _CategoryChallenge(
      category: 'Garden & Nature',
      description: 'Select items related to gardening or plants',
      targetItems: ['Watering Can', 'Rose Bush', 'Trowel', 'Flowerpot', 'Soil'],
      distractorItems: ['Toaster', 'Blanket', 'Mirror', 'Newspaper', 'Spoon'],
    ),
  ];

  late _CategoryChallenge _activeChallenge;
  late List<String> _currentItems;
  final Set<String> _selectedItems = {};
  bool _roundSubmitted = false;

  @override
  void initState() {
    super.initState();
    _stopwatch = Stopwatch()..start();

    if (widget.difficulty == GameDifficulty.focus) {
      _totalRounds = 2;
    } else {
      _totalRounds = 1;
    }

    _loadRound(0);
  }

  void _loadRound(int roundIdx) {
    _currentRound = roundIdx;
    _selectedItems.clear();
    _roundSubmitted = false;
    _activeChallenge = _challenges[roundIdx % _challenges.length];

    int targetCount;
    int distractorCount;
    if (widget.difficulty == GameDifficulty.gentle) {
      targetCount = 3;
      distractorCount = 3;
    } else if (widget.difficulty == GameDifficulty.standard) {
      targetCount = 4;
      distractorCount = 4;
    } else {
      targetCount = 4;
      distractorCount = 4;
    }

    final targets = _activeChallenge.targetItems.take(targetCount).toList();
    final distractors = _activeChallenge.distractorItems.take(distractorCount).toList();
    _currentItems = [...targets, ...distractors];
    _currentItems.shuffle();
  }

  void _toggleItem(String item) {
    if (_roundSubmitted) return;
    HapticFeedback.selectionClick();
    setState(() {
      if (_selectedItems.contains(item)) {
        _selectedItems.remove(item);
      } else {
        _selectedItems.add(item);
      }
    });
  }

  void _submitRound() {
    HapticFeedback.mediumImpact();
    final targets = _activeChallenge.targetItems.toSet();
    int correctThisRound = _selectedItems.intersection(targets).length;
    int mistakesThisRound = _selectedItems.difference(targets).length;

    _totalCorrect += correctThisRound;
    _totalMistakes += mistakesThisRound;
    _score += (correctThisRound * 60) - (mistakesThisRound * 25);
    if (_score < 0) _score = 0;

    setState(() {
      _roundSubmitted = true;
    });

    Future.delayed(const Duration(milliseconds: 1400), () {
      if (!mounted) return;
      if (_currentRound + 1 < _totalRounds) {
        setState(() {
          _loadRound(_currentRound + 1);
        });
      } else {
        _finishGame();
      }
    });
  }

  void _finishGame() {
    _stopwatch.stop();
    int expectedTotal = (widget.difficulty == GameDifficulty.gentle ? 3 : 4) * _totalRounds;
    double accuracy = (_totalCorrect / expectedTotal).clamp(0.0, 1.0);

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => GameResultScreen(
          gameTitle: 'Category Sorting',
          gameType: 'CATEGORY_SORT',
          difficulty: widget.difficulty,
          score: _score,
          accuracy: accuracy,
          reactionTimeMs: (_stopwatch.elapsedMilliseconds / expectedTotal).round(),
          mistakes: _totalMistakes,
          totalItems: expectedTotal,
          correctItems: _totalCorrect,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final targets = _activeChallenge.targetItems.toSet();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(
            Icons.arrow_back_ios_new_rounded,
            color: AppTheme.textPrimary,
          ),
          onPressed: () => Navigator.pop(context),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Category Sorting',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                fontSize: 18,
              ),
            ),
            if (_totalRounds > 1)
              Text(
                'Round ${_currentRound + 1} of $_totalRounds',
                style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
              ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: widget.difficulty.badgeBgColor,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: widget.difficulty.badgeBorderColor),
                ),
                child: Text(
                  widget.difficulty.label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: widget.difficulty.badgeTextColor,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Target Category Banner
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.borderSubtle),
                ),
                child: Column(
                  children: [
                    Text(
                      _activeChallenge.category,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primaryTealDark,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _activeChallenge.description,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppTheme.textSecondary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Items Grid
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 2.2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                  ),
                  itemCount: _currentItems.length,
                  itemBuilder: (ctx, idx) {
                    final item = _currentItems[idx];
                    final isSelected = _selectedItems.contains(item);
                    final isCorrect = targets.contains(item);

                    Color bgColor = Colors.white;
                    Color borderColor = AppTheme.borderSubtle;
                    Color textColor = AppTheme.textPrimary;

                    if (_roundSubmitted) {
                      if (isSelected && isCorrect) {
                        bgColor = AppTheme.gentleGreen;
                        borderColor = AppTheme.gentleGreen;
                        textColor = Colors.white;
                      } else if (isSelected && !isCorrect) {
                        bgColor = AppTheme.gentleRose;
                        borderColor = AppTheme.gentleRose;
                        textColor = Colors.white;
                      } else if (!isSelected && isCorrect) {
                        borderColor = AppTheme.gentleGreen;
                        textColor = AppTheme.gentleGreen;
                      }
                    } else if (isSelected) {
                      bgColor = AppTheme.tealSurface;
                      borderColor = AppTheme.primaryTeal;
                      textColor = AppTheme.primaryTealDark;
                    }

                    return GestureDetector(
                      onTap: () => _toggleItem(item),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: bgColor,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: borderColor, width: isSelected ? 1.8 : 1),
                        ),
                        child: Center(
                          child: Text(
                            item,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              color: textColor,
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 14),
              SizedBox(
                height: 52,
                child: ElevatedButton(
                  onPressed: (_selectedItems.isNotEmpty && !_roundSubmitted)
                      ? _submitRound
                      : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryTeal,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    _currentRound + 1 < _totalRounds ? 'Next Category' : 'Finish Challenge',
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
