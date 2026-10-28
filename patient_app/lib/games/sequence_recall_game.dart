import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import 'game_models.dart';
import 'game_result_screen.dart';

class SequenceRecallGameScreen extends StatefulWidget {
  final GameDifficulty difficulty;

  const SequenceRecallGameScreen({
    super.key,
    this.difficulty = GameDifficulty.standard,
  });

  @override
  State<SequenceRecallGameScreen> createState() =>
      _SequenceRecallGameScreenState();
}

class _SequenceRecallGameScreenState extends State<SequenceRecallGameScreen> {
  late List<Color> _tileColors;
  late List<String> _tileLabels;
  late int _tileCount;
  late int _maxRounds;
  late int _flashDurationMs;
  late int _pauseDurationMs;

  final List<int> _sequence = [];
  List<int> _userSequence = [];
  int? _activeHighlight;
  bool _isPlayingSequence = false;
  int _round = 1;
  int _score = 0;
  int _mistakes = 0;
  late Stopwatch _stopwatch;

  @override
  void initState() {
    super.initState();
    _stopwatch = Stopwatch()..start();

    if (widget.difficulty == GameDifficulty.gentle) {
      _tileColors = [
        const Color(0xFF0D9488), // Teal
        const Color(0xFFD97706), // Amber
        const Color(0xFF4338CA), // Indigo
      ];
      _tileLabels = ['Teal', 'Amber', 'Indigo'];
      _tileCount = 3;
      _maxRounds = 3;
      _flashDurationMs = 850;
      _pauseDurationMs = 350;
    } else if (widget.difficulty == GameDifficulty.focus) {
      _tileColors = [
        const Color(0xFF0D9488), // Teal
        const Color(0xFFD97706), // Amber
        const Color(0xFF4338CA), // Indigo
        const Color(0xFFE11D48), // Rose
      ];
      _tileLabels = ['Teal', 'Amber', 'Indigo', 'Rose'];
      _tileCount = 4;
      _maxRounds = 7;
      _flashDurationMs = 450;
      _pauseDurationMs = 200;
    } else {
      _tileColors = [
        const Color(0xFF0D9488), // Teal
        const Color(0xFFD97706), // Amber
        const Color(0xFF4338CA), // Indigo
        const Color(0xFFE11D48), // Rose
      ];
      _tileLabels = ['Teal', 'Amber', 'Indigo', 'Rose'];
      _tileCount = 4;
      _maxRounds = 5;
      _flashDurationMs = 650;
      _pauseDurationMs = 260;
    }

    _startRound();
  }

  void _startRound() {
    setState(() {
      _userSequence = [];
      _sequence.add((_sequence.length + DateTime.now().millisecond) % _tileCount);
      _isPlayingSequence = true;
    });
    _playSequence();
  }

  Future<void> _playSequence() async {
    await Future.delayed(const Duration(milliseconds: 600));
    for (int index in _sequence) {
      if (!mounted) return;
      setState(() => _activeHighlight = index);
      HapticFeedback.lightImpact();
      await Future.delayed(Duration(milliseconds: _flashDurationMs));
      if (!mounted) return;
      setState(() => _activeHighlight = null);
      await Future.delayed(Duration(milliseconds: _pauseDurationMs));
    }
    if (mounted) {
      setState(() => _isPlayingSequence = false);
    }
  }

  void _onTileTap(int index) {
    if (_isPlayingSequence) return;

    HapticFeedback.selectionClick();
    setState(() => _activeHighlight = index);
    Timer(const Duration(milliseconds: 200), () {
      if (mounted) setState(() => _activeHighlight = null);
    });

    _userSequence.add(index);
    int currentStep = _userSequence.length - 1;

    if (_userSequence[currentStep] != _sequence[currentStep]) {
      // Mistake
      _mistakes++;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Noticeable pattern mismatch. Session concluding gently.'),
          backgroundColor: AppTheme.warmAmber,
          duration: Duration(seconds: 1),
        ),
      );
      _finishGame();
    } else if (_userSequence.length == _sequence.length) {
      // Round cleared!
      _score += _round * 50;
      if (_round >= _maxRounds) {
        _finishGame();
      } else {
        setState(() => _round++);
        Timer(const Duration(milliseconds: 800), _startRound);
      }
    }
  }

  void _finishGame() {
    _stopwatch.stop();
    final elapsedMs = _stopwatch.elapsedMilliseconds;
    final total = _sequence.length;
    final correct = _userSequence.length;
    final accuracy = total > 0 ? (correct / total).clamp(0.0, 1.0) : 0.0;

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => GameResultScreen(
          gameTitle: 'Sequence Pattern Recall',
          gameType: 'SEQUENCE_RECALL',
          difficulty: widget.difficulty,
          score: _score,
          accuracy: accuracy,
          reactionTimeMs: (elapsedMs / (total > 0 ? total : 1)).round(),
          mistakes: _mistakes,
          totalItems: total,
          correctItems: correct,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Row(
          children: [
            const Text(
              'Sequence Recall',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
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
        backgroundColor: Colors.white,
        foregroundColor: AppTheme.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.borderSubtle),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Round: $_round / $_maxRounds',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                        color: AppTheme.primaryTealDark,
                      ),
                    ),
                    Text(
                      'Score: $_score',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _isPlayingSequence
                    ? 'Watch the pattern sequence carefully'
                    : 'Your turn: Tap the pads in identical order',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 20),

              // Interactive Tile Grid
              Expanded(
                child: GridView.count(
                  crossAxisCount: _tileCount == 3 ? 1 : 2,
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                  childAspectRatio: _tileCount == 3 ? 2.5 : 1.1,
                  children: List.generate(_tileCount, (index) {
                    final isHighlighted = _activeHighlight == index;
                    return GestureDetector(
                      onTap: () => _onTileTap(index),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        decoration: BoxDecoration(
                          color: isHighlighted
                              ? _tileColors[index]
                              : _tileColors[index].withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(
                            color: _tileColors[index],
                            width: isHighlighted ? 3 : 1.5,
                          ),
                        ),
                        child: Center(
                          child: Text(
                            _tileLabels[index],
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w800,
                              color: isHighlighted ? Colors.white : _tileColors[index],
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

