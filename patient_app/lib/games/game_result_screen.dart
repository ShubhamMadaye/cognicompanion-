import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/patient_provider.dart';
import '../services/api_service.dart';
import 'game_models.dart';

class GameResultScreen extends StatefulWidget {
  final String gameTitle;
  final String gameType;
  final int score;
  final double accuracy;
  final int reactionTimeMs;
  final int mistakes;
  final int totalItems;
  final int correctItems;
  final GameDifficulty difficulty;

  const GameResultScreen({
    super.key,
    required this.gameTitle,
    required this.gameType,
    required this.score,
    required this.accuracy,
    required this.reactionTimeMs,
    required this.mistakes,
    required this.totalItems,
    required this.correctItems,
    this.difficulty = GameDifficulty.standard,
  });

  @override
  State<GameResultScreen> createState() => _GameResultScreenState();
}

class _GameResultScreenState extends State<GameResultScreen>
    with SingleTickerProviderStateMixin {
  bool _submitted = false;
  late AnimationController _scaleController;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    _scaleAnimation =
        CurvedAnimation(parent: _scaleController, curve: Curves.elasticOut);
    _scaleController.forward();
    WidgetsBinding.instance.addPostFrameCallback((_) => _submitSession());
  }

  @override
  void dispose() {
    _scaleController.dispose();
    super.dispose();
  }

  Future<void> _submitSession() async {
    if (_submitted || !mounted) return;
    _submitted = true;
    final patientId = context.read<PatientProvider>().profile.id;
    await ApiService.submitGameSession(
      patientId: patientId,
      gameType: widget.gameType,
      difficulty: widget.difficulty.apiValue,
      score: widget.score,
      totalItems: widget.totalItems,
      correctItems: widget.correctItems,
      reactionTimeMs: widget.reactionTimeMs,
      mistakes: widget.mistakes,
    );
  }

  /// Score out of 10
  int get _scoreOutOf10 {
    final maxPossible = widget.totalItems * 100;
    if (maxPossible == 0) return 8;
    return ((widget.score / maxPossible) * 10).round().clamp(1, 10);
  }

  String get _message {
    final s = _scoreOutOf10;
    if (s >= 9) {
      return "Perfect! Excellent!";
    }

    if (s >= 7) {
      return "Great job! Let's try\nsomething a little more\nchallenging!";
    }

    if (s >= 5) {
      return "Good effort!\nKeep practicing!";
    }

    return "Nice try!\nYou'll do better next time!";
  }

  @override
  Widget build(BuildContext context) {
    final name = context.read<PatientProvider>().profile.firstName;
    final s = _scoreOutOf10;

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 24),

                // ── Distinguished Achievement Badge ──────────────────────
                ScaleTransition(
                  scale: _scaleAnimation,
                  child: Container(
                    width: 68,
                    height: 68,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: const Color(0xFFFEF3C7),
                      border:
                          Border.all(color: const Color(0xFFF59E0B), width: 2),
                    ),
                    child: const Icon(
                      Icons.workspace_premium_rounded,
                      color: Color(0xFFB45309),
                      size: 38,
                    ),
                  ),
                ),
                const SizedBox(height: 18),

                // ── Score circle ─────────────────────────────────────────
                ScaleTransition(
                  scale: _scaleAnimation,
                  child: Container(
                    width: 130,
                    height: 130,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: AppTheme.primaryTeal,
                        width: 4.5,
                      ),
                      color: Colors.white,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text('$s',
                            style: const TextStyle(
                                fontSize: 46,
                                fontWeight: FontWeight.w900,
                                color: AppTheme.primaryTeal,
                                height: 1.0)),
                        const Text('/10',
                            style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textSecondary)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // ── "Great job, Shanti!" ──────────────────────────────────
                Text('Great job, $name!',
                    style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.textPrimary)),
                const SizedBox(height: 10),
                Text(_message,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontSize: 16,
                        color: AppTheme.textSecondary,
                        height: 1.5)),
                const SizedBox(height: 14),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    color: widget.difficulty.bgColor,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                        color: widget.difficulty.color.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(widget.difficulty.icon,
                          size: 14, color: widget.difficulty.color),
                      const SizedBox(width: 5),
                      Text(
                        '${widget.difficulty.label} Level',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: widget.difficulty.color,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // ── Stats row ────────────────────────────────────────────
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: AppTheme.cardDecoration,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _stat('Score', '${widget.score}', Icons.star_rounded,
                          AppTheme.warmAmber),
                      _stat(
                          'Correct',
                          '${widget.correctItems}/${widget.totalItems}',
                          Icons.check_circle_rounded,
                          AppTheme.gentleGreen),
                      _stat('Mistakes', '${widget.mistakes}',
                          Icons.close_rounded, AppTheme.gentleRose),
                    ],
                  ),
                ),
                const SizedBox(height: 36),

                // ── Buttons ──────────────────────────────────────────────
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () =>
                            Navigator.pop(context), // goes back to game
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.primaryTeal,
                          side: const BorderSide(
                              color: AppTheme.primaryTeal, width: 2),
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14)),
                          textStyle: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.w700),
                        ),
                        child: const Text('Play Again'),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          // Pop back to games overview
                          Navigator.popUntil(context,
                              (r) => r.isFirst || r.settings.name == '/');
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primaryTeal,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14)),
                          elevation: 0,
                          textStyle: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.w700),
                        ),
                        child: const Text('Done'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _stat(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(value,
            style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary)),
        Text(label,
            style:
                const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
      ],
    );
  }
}
