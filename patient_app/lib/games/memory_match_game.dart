import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import 'game_result_screen.dart';

import 'game_models.dart';

class CardItem {
  final int id;
  final String initial;
  final String label;
  final String role;
  final Color color;
  bool isFaceUp;
  bool isMatched;

  CardItem({
    required this.id,
    required this.initial,
    required this.label,
    required this.role,
    required this.color,
    this.isFaceUp = false,
    this.isMatched = false,
  });
}

class MemoryMatchGameScreen extends StatefulWidget {
  final GameDifficulty difficulty;

  const MemoryMatchGameScreen({
    super.key,
    this.difficulty = GameDifficulty.standard,
  });

  @override
  State<MemoryMatchGameScreen> createState() => _MemoryMatchGameScreenState();
}

class _MemoryMatchGameScreenState extends State<MemoryMatchGameScreen> {
  late List<CardItem> _cards;
  CardItem? _firstSelected;
  CardItem? _secondSelected;
  bool _isProcessing = false;
  int _score = 0;
  int _mistakes = 0;
  int _matchedPairs = 0;
  late Stopwatch _stopwatch;
  late List<Map<String, dynamic>> _pairs;

  // Family portraits — dignified clinical memory stimulation
  static const List<Map<String, dynamic>> _allPairs = [
    {
      'initial': 'R',
      'label': 'Rahul',
      'role': 'Son',
      'color': AppTheme.primaryTealDark,
    },
    {
      'initial': 'P',
      'label': 'Priya',
      'role': 'Daughter',
      'color': Color(0xFFB45309),
    },
    {
      'initial': 'A',
      'label': 'Amit',
      'role': 'Grandson',
      'color': Color(0xFF1E3A8A),
    },
    {
      'initial': 'M',
      'label': 'Meera',
      'role': 'Granddaughter',
      'color': Color(0xFF15803D),
    },
    {
      'initial': 'S',
      'label': 'Suresh',
      'role': 'Brother',
      'color': Color(0xFF7C3AED),
    },
    {
      'initial': 'A',
      'label': 'Anjali',
      'role': 'Niece',
      'color': Color(0xFFDB2777),
    },
  ];

  @override
  void initState() {
    super.initState();
    final pairCount = widget.difficulty == GameDifficulty.gentle
        ? 3
        : widget.difficulty == GameDifficulty.focus
            ? 6
            : 4;
    _pairs = _allPairs.take(pairCount).toList();
    _initGame();
  }

  void _initGame() {
    _cards = [];
    int id = 0;
    for (var p in _pairs) {
      _cards.add(
        CardItem(
          id: id++,
          initial: p['initial'] as String,
          label: p['label'] as String,
          role: p['role'] as String,
          color: p['color'] as Color,
        ),
      );
      _cards.add(
        CardItem(
          id: id++,
          initial: p['initial'] as String,
          label: p['label'] as String,
          role: p['role'] as String,
          color: p['color'] as Color,
        ),
      );
    }
    _cards.shuffle();
    _firstSelected = null;
    _secondSelected = null;
    _isProcessing = false;
    _score = 0;
    _mistakes = 0;
    _matchedPairs = 0;
    _stopwatch = Stopwatch()..start();
  }

  void _onCardTap(CardItem card) {
    if (_isProcessing || card.isFaceUp || card.isMatched) return;
    HapticFeedback.selectionClick();
    setState(() => card.isFaceUp = true);
    if (_firstSelected == null) {
      _firstSelected = card;
    } else {
      _secondSelected = card;
      _isProcessing = true;
      _checkMatch();
    }
  }

  void _checkMatch() {
    if (_firstSelected!.label == _secondSelected!.label) {
      HapticFeedback.mediumImpact();
      setState(() {
        _firstSelected!.isMatched = true;
        _secondSelected!.isMatched = true;
        _matchedPairs++;
        _score += 100;
        _firstSelected = null;
        _secondSelected = null;
        _isProcessing = false;
      });
      if (_matchedPairs == _pairs.length) _finishGame();
    } else {
      _mistakes++;
      Timer(const Duration(milliseconds: 1000), () {
        if (mounted) {
          setState(() {
            _firstSelected!.isFaceUp = false;
            _secondSelected!.isFaceUp = false;
            _firstSelected = null;
            _secondSelected = null;
            _isProcessing = false;
          });
        }
      });
    }
  }

  void _finishGame() {
    _stopwatch.stop();
    final totalItems = _pairs.length * 2;
    final accuracy = (totalItems / (totalItems + _mistakes)).clamp(0.0, 1.0);
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => GameResultScreen(
          gameTitle: 'Family Memory Match',
          gameType: 'MEMORY_MATCH',
          difficulty: widget.difficulty,
          score: _score,
          accuracy: accuracy,
          reactionTimeMs:
              (_stopwatch.elapsedMilliseconds / totalItems).round(),
          mistakes: _mistakes,
          totalItems: totalItems,
          correctItems: totalItems,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isFocus = widget.difficulty == GameDifficulty.focus;

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
            Row(
              children: [
                const Text(
                  'Memory Match',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                    fontSize: 18,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: widget.difficulty.bgColor,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: widget.difficulty.color.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    widget.difficulty.label,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: widget.difficulty.color,
                    ),
                  ),
                ),
              ],
            ),
            const Text(
              'Find the matching family members',
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
          ],
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Score bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.family_restroom_rounded,
                        color: AppTheme.primaryTeal,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Pairs: $_matchedPairs / ${_pairs.length}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      const Icon(
                        Icons.star_rounded,
                        color: AppTheme.warmAmber,
                        size: 20,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '$_score',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Responsive card grid with dignified family portrait tokens
            Expanded(
              child: GridView.builder(
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: isFocus ? 3 : 2,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: isFocus ? 0.82 : 0.95,
                ),
                itemCount: _cards.length,
                itemBuilder: (context, index) {
                  final card = _cards[index];
                  final isRevealed = card.isFaceUp || card.isMatched;

                  return GestureDetector(
                    onTap: () => _onCardTap(card),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      decoration: BoxDecoration(
                        color: isRevealed ? Colors.white : AppTheme.primaryTealDark,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: card.isMatched
                              ? AppTheme.gentleGreen
                              : isRevealed
                                  ? AppTheme.borderStone
                                  : AppTheme.primaryTealDark,
                          width: card.isMatched ? 2.5 : 1.2,
                        ),
                      ),
                      child: Center(
                        child: isRevealed
                            ? Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    width: 52,
                                    height: 52,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: card.color,
                                      border: Border.all(
                                        color: AppTheme.borderStone,
                                        width: 1.5,
                                      ),
                                    ),
                                    child: Center(
                                      child: Text(
                                        card.initial,
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 24,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    card.label,
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w800,
                                      color: AppTheme.textPrimary,
                                    ),
                                  ),
                                  Text(
                                    card.role,
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                      color: AppTheme.textSecondary,
                                    ),
                                  ),
                                ],
                              )
                            : const Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.favorite_rounded,
                                    size: 32,
                                    color: Colors.white70,
                                  ),
                                  SizedBox(height: 4),
                                  Text(
                                    'TAP TO FLIP',
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.8,
                                      color: Colors.white70,
                                    ),
                                  ),
                                ],
                              ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
