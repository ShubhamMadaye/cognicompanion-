import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import 'game_models.dart';
import 'game_result_screen.dart';

class PictureRecallGameScreen extends StatefulWidget {
  final GameDifficulty difficulty;

  const PictureRecallGameScreen({
    super.key,
    this.difficulty = GameDifficulty.gentle,
  });

  @override
  State<PictureRecallGameScreen> createState() =>
      _PictureRecallGameScreenState();
}

class _PictureRecallGameScreenState extends State<PictureRecallGameScreen> {
  int _currentIndex = 0;
  int _score = 0;
  int _correctCount = 0;
  int _mistakes = 0;
  int? _selectedAnswer;
  bool _answered = false;
  late Stopwatch _stopwatch;
  late List<Map<String, dynamic>> _questions;

  // Master clinical portrait bank
  final List<Map<String, dynamic>> _allQuestions = [
    {
      'initial': 'R',
      'name': 'Rahul Sharma',
      'role': 'Son · Primary Caregiver',
      'avatarColor': AppTheme.primaryTealDark,
      'question': 'Who is shown in this family portrait?',
      'options': ['Rahul', 'Priya', 'Amit', 'Meera'],
      'gentleOptions': ['Rahul', 'Amit'],
      'answer': 'Rahul',
      'hint': 'Your son who helps with morning medicines',
    },
    {
      'initial': 'P',
      'name': 'Priya Sharma',
      'role': 'Daughter · Sunday Lunch Visit',
      'avatarColor': const Color(0xFFB45309),
      'question': 'Who visited you for Sunday lunch?',
      'options': ['Priya', 'Rahul', 'Amit', 'Meera'],
      'gentleOptions': ['Priya', 'Meera'],
      'answer': 'Priya',
      'hint': 'Your daughter who brings homemade sweets',
    },
    {
      'initial': 'A',
      'name': 'Amit Sharma',
      'role': 'Grandson · High School Soccer',
      'avatarColor': const Color(0xFF1E3A8A),
      'question': 'Whose school photo is this?',
      'options': ['Amit', 'Meera', 'Rahul', 'Priya'],
      'gentleOptions': ['Amit', 'Rahul'],
      'answer': 'Amit',
      'hint': 'Your grandson wearing his school jersey',
    },
    {
      'initial': 'M',
      'name': 'Meera Verma',
      'role': 'Sister · Evening Phone Calls',
      'avatarColor': const Color(0xFF7C3AED),
      'question': 'Who calls you every evening at 6 PM?',
      'options': ['Meera', 'Priya', 'Ananya', 'Sunita'],
      'gentleOptions': ['Meera', 'Sunita'],
      'answer': 'Meera',
      'hint': 'Your elder sister living in Pune',
    },
    {
      'initial': 'D',
      'name': 'Dr. Kulkarni',
      'role': 'Family Doctor · Monthly Visit',
      'avatarColor': const Color(0xFF0F766E),
      'question': 'Who is your trusted family physician?',
      'options': ['Dr. Kulkarni', 'Dr. Joshi', 'Dr. Sen', 'Dr. Roy'],
      'gentleOptions': ['Dr. Kulkarni', 'Dr. Joshi'],
      'answer': 'Dr. Kulkarni',
      'hint': 'Visits every first Monday of the month',
    },
  ];

  @override
  void initState() {
    super.initState();
    _stopwatch = Stopwatch()..start();

    // Scale questions based on difficulty
    if (widget.difficulty == GameDifficulty.gentle) {
      _questions = _allQuestions.take(3).toList();
    } else if (widget.difficulty == GameDifficulty.standard) {
      _questions = _allQuestions.take(4).toList();
    } else {
      _questions = List.from(_allQuestions);
    }
  }

  void _selectAnswer(int idx, List<String> options) {
    if (_answered) return;
    HapticFeedback.selectionClick();
    final correct = options[idx] == _questions[_currentIndex]['answer'];
    setState(() {
      _selectedAnswer = idx;
      _answered = true;
    });
    if (correct) {
      _score += 100;
      _correctCount++;
    } else {
      _mistakes++;
    }

    Future.delayed(const Duration(milliseconds: 900), () {
      if (!mounted) return;
      if (_currentIndex < _questions.length - 1) {
        setState(() {
          _currentIndex++;
          _selectedAnswer = null;
          _answered = false;
        });
      } else {
        _finishGame();
      }
    });
  }

  void _finishGame() {
    _stopwatch.stop();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => GameResultScreen(
          gameTitle: 'Picture Recall',
          gameType: 'PICTURE_RECALL',
          difficulty: widget.difficulty,
          score: _score,
          accuracy: _correctCount / _questions.length,
          reactionTimeMs:
              (_stopwatch.elapsedMilliseconds / _questions.length).round(),
          mistakes: _mistakes,
          totalItems: _questions.length,
          correctItems: _correctCount,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final q = _questions[_currentIndex];
    final options = (widget.difficulty == GameDifficulty.gentle
            ? (q['gentleOptions'] as List<String>)
            : (q['options'] as List<String>));

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
              'Picture Recall',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                fontSize: 18,
              ),
            ),
            Text(
              'Question ${_currentIndex + 1} of ${_questions.length}',
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
              // Progress dots
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(_questions.length, (i) {
                  return Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == _currentIndex ? 24 : 8,
                    height: 6,
                    decoration: BoxDecoration(
                      color: i <= _currentIndex
                          ? AppTheme.primaryTeal
                          : Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  );
                }),
              ),
              const SizedBox(height: 18),

              // Large memory portrait card
              Expanded(
                flex: 5,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 84,
                        height: 84,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: q['avatarColor'] as Color,
                          border: Border.all(color: AppTheme.borderStone, width: 2),
                        ),
                        child: Center(
                          child: Text(
                            q['initial'] as String,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 36,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: AppTheme.warmSurface,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppTheme.borderStone),
                        ),
                        child: Text(
                          q['role'] as String,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ),
                      if (widget.difficulty == GameDifficulty.gentle &&
                          q['hint'] != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          q['hint'] as String,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 12,
                            fontStyle: FontStyle.italic,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Question text
              Text(
                q['question'] as String,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 16),

              // Option buttons
              Expanded(
                flex: 4,
                child: GridView.count(
                  crossAxisCount: options.length <= 2 ? 1 : 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: options.length <= 2 ? 4.0 : 2.2,
                  children: List.generate(options.length, (i) {
                    Color btnColor = Colors.white;
                    Color textColor = AppTheme.textPrimary;
                    Color borderColor = AppTheme.borderSubtle;

                    if (_answered && _selectedAnswer == i) {
                      final isCorrect = options[i] == q['answer'];
                      btnColor =
                          isCorrect ? AppTheme.gentleGreen : AppTheme.gentleRose;
                      textColor = Colors.white;
                      borderColor = btnColor;
                    } else if (_answered && options[i] == q['answer']) {
                      btnColor = AppTheme.gentleGreen;
                      textColor = Colors.white;
                      borderColor = btnColor;
                    }

                    return GestureDetector(
                      onTap: () => _selectAnswer(i, options),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        decoration: BoxDecoration(
                          color: btnColor,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: borderColor, width: 1.5),
                        ),
                        child: Center(
                          child: Text(
                            options[i],
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: textColor,
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
