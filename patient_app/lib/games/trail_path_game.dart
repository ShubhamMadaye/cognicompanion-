import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import 'game_models.dart';
import 'game_result_screen.dart';

class TrailPathGameScreen extends StatefulWidget {
  final GameDifficulty difficulty;

  const TrailPathGameScreen({
    super.key,
    this.difficulty = GameDifficulty.gentle,
  });

  @override
  State<TrailPathGameScreen> createState() => _TrailPathGameScreenState();
}

class _TrailNode {
  final String label;
  final int order;
  final Offset position; // Relative 0.0 -> 1.0 within play area

  const _TrailNode({
    required this.label,
    required this.order,
    required this.position,
  });
}

class _TrailPathGameScreenState extends State<TrailPathGameScreen> {
  late Stopwatch _stopwatch;
  int _nextOrder = 1;
  int _mistakes = 0;
  int _score = 0;
  late List<_TrailNode> _nodes;

  @override
  void initState() {
    super.initState();
    _stopwatch = Stopwatch()..start();
    _initializeNodes();
  }

  void _initializeNodes() {
    if (widget.difficulty == GameDifficulty.gentle) {
      // 5 numbers in well-spaced layout
      _nodes = const [
        _TrailNode(label: '1', order: 1, position: Offset(0.20, 0.22)),
        _TrailNode(label: '2', order: 2, position: Offset(0.76, 0.18)),
        _TrailNode(label: '3', order: 3, position: Offset(0.50, 0.50)),
        _TrailNode(label: '4', order: 4, position: Offset(0.22, 0.78)),
        _TrailNode(label: '5', order: 5, position: Offset(0.80, 0.75)),
      ];
    } else if (widget.difficulty == GameDifficulty.standard) {
      // 8 numbers
      _nodes = const [
        _TrailNode(label: '1', order: 1, position: Offset(0.20, 0.15)),
        _TrailNode(label: '2', order: 2, position: Offset(0.78, 0.16)),
        _TrailNode(label: '3', order: 3, position: Offset(0.35, 0.38)),
        _TrailNode(label: '4', order: 4, position: Offset(0.82, 0.44)),
        _TrailNode(label: '5', order: 5, position: Offset(0.18, 0.60)),
        _TrailNode(label: '6', order: 6, position: Offset(0.58, 0.64)),
        _TrailNode(label: '7', order: 7, position: Offset(0.30, 0.84)),
        _TrailNode(label: '8', order: 8, position: Offset(0.80, 0.82)),
      ];
    } else {
      // Focus: Alternating Numbers & Letters (TMT-B clinical standard: 1 -> A -> 2 -> B -> 3 -> C...)
      _nodes = const [
        _TrailNode(label: '1', order: 1, position: Offset(0.18, 0.14)),
        _TrailNode(label: 'A', order: 2, position: Offset(0.78, 0.15)),
        _TrailNode(label: '2', order: 3, position: Offset(0.32, 0.34)),
        _TrailNode(label: 'B', order: 4, position: Offset(0.82, 0.38)),
        _TrailNode(label: '3', order: 5, position: Offset(0.22, 0.58)),
        _TrailNode(label: 'C', order: 6, position: Offset(0.65, 0.58)),
        _TrailNode(label: '4', order: 7, position: Offset(0.28, 0.82)),
        _TrailNode(label: 'D', order: 8, position: Offset(0.80, 0.80)),
      ];
    }
  }

  void _onNodeTap(_TrailNode node) {
    if (node.order < _nextOrder) return; // already completed

    if (node.order == _nextOrder) {
      HapticFeedback.lightImpact();
      setState(() {
        _nextOrder++;
        _score += 40;
      });

      if (_nextOrder > _nodes.length) {
        _finishGame();
      }
    } else {
      HapticFeedback.mediumImpact();
      setState(() {
        _mistakes++;
        if (_score >= 10) _score -= 10;
      });
    }
  }

  void _finishGame() {
    _stopwatch.stop();
    int total = _nodes.length;
    double accuracy = (total / (total + _mistakes)).clamp(0.0, 1.0);

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => GameResultScreen(
          gameTitle: 'Trail Path',
          gameType: 'TRAIL_MAKING',
          difficulty: widget.difficulty,
          score: _score,
          accuracy: accuracy,
          reactionTimeMs: (_stopwatch.elapsedMilliseconds / total).round(),
          mistakes: _mistakes,
          totalItems: total,
          correctItems: total,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    String instruction;
    if (widget.difficulty == GameDifficulty.focus) {
      instruction = 'Connect alternately: 1 → A → 2 → B → 3 → D';
    } else {
      instruction = 'Tap the numbers in order: 1 → 2 → 3...';
    }

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
              'Trail Path',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                fontSize: 18,
              ),
            ),
            Text(
              'Target ${_nextOrder <= _nodes.length ? _nodes.firstWhere((n) => n.order == _nextOrder).label : "Done"}',
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
              // Instruction Banner
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.borderSubtle),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.navigation_outlined,
                      size: 20,
                      color: AppTheme.primaryTeal,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        instruction,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Interactive Trail Canvas
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final double w = constraints.maxWidth;
                      final double h = constraints.maxHeight;
                      const double nodeSize = 54;

                      return Stack(
                        children: [
                          // Connected lines
                          CustomPaint(
                            size: Size(w, h),
                            painter: _TrailPathPainter(
                              nodes: _nodes,
                              currentOrder: _nextOrder,
                              nodeSize: nodeSize,
                            ),
                          ),

                          // Node circles
                          ..._nodes.map((node) {
                            final bool isCompleted = node.order < _nextOrder;
                            final bool isNext = node.order == _nextOrder;

                            Color circleBg = Colors.white;
                            Color borderCol = AppTheme.borderSubtle;
                            Color textCol = AppTheme.textPrimary;

                            if (isCompleted) {
                              circleBg = AppTheme.gentleGreen;
                              borderCol = AppTheme.gentleGreen;
                              textCol = Colors.white;
                            } else if (isNext) {
                              circleBg = AppTheme.tealSurface;
                              borderCol = AppTheme.primaryTeal;
                              textCol = AppTheme.primaryTealDark;
                            }

                            final double left = (node.position.dx * (w - nodeSize)).clamp(8.0, w - nodeSize - 8.0);
                            final double top = (node.position.dy * (h - nodeSize)).clamp(8.0, h - nodeSize - 8.0);

                            return Positioned(
                              left: left,
                              top: top,
                              child: GestureDetector(
                                onTap: () => _onNodeTap(node),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  width: nodeSize,
                                  height: nodeSize,
                                  decoration: BoxDecoration(
                                    color: circleBg,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: borderCol,
                                      width: isNext ? 2.5 : 1.5,
                                    ),
                                  ),
                                  child: Center(
                                    child: Text(
                                      node.label,
                                      style: TextStyle(
                                        fontSize: 20,
                                        fontWeight: FontWeight.w800,
                                        color: textCol,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }),
                        ],
                      );
                    },
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

class _TrailPathPainter extends CustomPainter {
  final List<_TrailNode> nodes;
  final int currentOrder;
  final double nodeSize;

  _TrailPathPainter({
    required this.nodes,
    required this.currentOrder,
    required this.nodeSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (currentOrder <= 1) return;

    final paint = Paint()
      ..color = AppTheme.primaryTeal.withValues(alpha: 0.6)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final path = Path();
    bool first = true;

    for (int i = 1; i < currentOrder && i <= nodes.length; i++) {
      final node = nodes.firstWhere((n) => n.order == i);
      final double x = (node.position.dx * (size.width - nodeSize)).clamp(8.0, size.width - nodeSize - 8.0) + (nodeSize / 2);
      final double y = (node.position.dy * (size.height - nodeSize)).clamp(8.0, size.height - nodeSize - 8.0) + (nodeSize / 2);

      if (first) {
        path.moveTo(x, y);
        first = false;
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _TrailPathPainter oldDelegate) {
    return oldDelegate.currentOrder != currentOrder;
  }
}
