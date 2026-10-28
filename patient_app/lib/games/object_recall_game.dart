import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme/app_theme.dart';
import 'game_models.dart';
import 'game_result_screen.dart';

class ObjectItem {
  final String name;
  final IconData icon;
  final Color color;

  const ObjectItem({
    required this.name,
    required this.icon,
    required this.color,
  });
}

class ObjectRecallGameScreen extends StatefulWidget {
  final GameDifficulty difficulty;

  const ObjectRecallGameScreen({
    super.key,
    this.difficulty = GameDifficulty.gentle,
  });

  @override
  State<ObjectRecallGameScreen> createState() => _ObjectRecallGameScreenState();
}

class _ObjectRecallGameScreenState extends State<ObjectRecallGameScreen> {
  bool _isViewingTray = true;
  late int _countdown;
  Timer? _timer;
  late Stopwatch _stopwatch;

  // Master bank of domestic objects
  final List<ObjectItem> _masterObjects = const [
    ObjectItem(
      name: 'Spectacles',
      icon: Icons.visibility_rounded,
      color: AppTheme.primaryTealDark,
    ),
    ObjectItem(
      name: 'House Keys',
      icon: Icons.vpn_key_rounded,
      color: Color(0xFFB45309),
    ),
    ObjectItem(
      name: 'Reading Book',
      icon: Icons.menu_book_rounded,
      color: Color(0xFF1E3A8A),
    ),
    ObjectItem(
      name: 'Tea Pot',
      icon: Icons.coffee_rounded,
      color: Color(0xFF15803D),
    ),
    ObjectItem(
      name: 'Wrist Watch',
      icon: Icons.watch_later_rounded,
      color: Color(0xFF4338CA),
    ),
    ObjectItem(
      name: 'Umbrella',
      icon: Icons.umbrella_rounded,
      color: Color(0xFF7C2D12),
    ),
    ObjectItem(
      name: 'Water Bottle',
      icon: Icons.local_drink_rounded,
      color: Color(0xFF0284C7),
    ),
    ObjectItem(
      name: 'Radio',
      icon: Icons.radio_rounded,
      color: Color(0xFF6B21A8),
    ),
  ];

  late List<ObjectItem> _trayItems;
  late List<ObjectItem> _selectionPool;
  final Set<String> _selectedNames = {};

  @override
  void initState() {
    super.initState();
    _stopwatch = Stopwatch()..start();

    int trayCount;
    int poolCount;
    if (widget.difficulty == GameDifficulty.gentle) {
      trayCount = 3;
      _countdown = 8;
      poolCount = 4;
    } else if (widget.difficulty == GameDifficulty.standard) {
      trayCount = 4;
      _countdown = 5;
      poolCount = 6;
    } else {
      trayCount = 5;
      _countdown = 4;
      poolCount = 8;
    }

    _trayItems = _masterObjects.take(trayCount).toList();
    _selectionPool = _masterObjects.take(poolCount).toList();
    // Shuffle pool for selection view
    _selectionPool.shuffle();

    _startCountdown();
  }

  void _startCountdown() {
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_countdown > 1) {
        setState(() => _countdown--);
      } else {
        _timer?.cancel();
        setState(() => _isViewingTray = false);
      }
    });
  }

  void _toggleSelection(String name) {
    HapticFeedback.selectionClick();
    setState(() {
      if (_selectedNames.contains(name)) {
        _selectedNames.remove(name);
      } else {
        _selectedNames.add(name);
      }
    });
  }

  void _finishGame() {
    _stopwatch.stop();
    final correctSet = _trayItems.map((e) => e.name).toSet();
    int correctCount = _selectedNames.intersection(correctSet).length;
    int mistakes = _selectedNames.difference(correctSet).length;
    int total = _trayItems.length;
    double accuracy = (correctCount / total).clamp(0.0, 1.0);
    int score = (correctCount * 50) - (mistakes * 20);

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => GameResultScreen(
          gameTitle: 'Everyday Object Recall',
          gameType: 'OBJECT_RECALL',
          difficulty: widget.difficulty,
          score: score < 0 ? 0 : score,
          accuracy: accuracy,
          reactionTimeMs: (_stopwatch.elapsedMilliseconds / total).round(),
          mistakes: mistakes,
          totalItems: total,
          correctItems: correctCount,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text(
          'Everyday Object Recall',
          style: TextStyle(
            fontWeight: FontWeight.w800,
            color: AppTheme.textPrimary,
            fontSize: 18,
          ),
        ),
        backgroundColor: AppTheme.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(
            Icons.arrow_back_ios_new_rounded,
            color: AppTheme.textPrimary,
          ),
          onPressed: () => Navigator.pop(context),
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
          child: _isViewingTray ? _buildTrayView() : _buildSelectionView(),
        ),
      ),
    );
  }

  Widget _buildTrayView() {
    return Column(
      children: [
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
              const Expanded(
                child: Text(
                  'Remember the items on the tray',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.warmSurface,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.borderStone),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.timer_outlined, size: 16, color: AppTheme.amberAccent),
                    const SizedBox(width: 4),
                    Text(
                      '${_countdown}s',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                        color: AppTheme.amberAccent,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppTheme.borderSubtle),
            ),
            child: GridView.builder(
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: _trayItems.length <= 3 ? 1 : 2,
                childAspectRatio: _trayItems.length <= 3 ? 3.5 : 1.3,
                crossAxisSpacing: 14,
                mainAxisSpacing: 14,
              ),
              itemCount: _trayItems.length,
              itemBuilder: (ctx, idx) {
                final item = _trayItems[idx];
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppTheme.warmSurface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderStone),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: item.color.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(item.icon, color: item.color, size: 28),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Text(
                          item.name,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: OutlinedButton(
            onPressed: () {
              _timer?.cancel();
              setState(() => _isViewingTray = false);
            },
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppTheme.primaryTeal),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: const Text(
              'I am Ready',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 15,
                color: AppTheme.primaryTeal,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSelectionView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.borderSubtle),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Select the ${_trayItems.length} items you saw',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                  color: AppTheme.textPrimary,
                ),
              ),
              Text(
                '${_selectedNames.length}/${_trayItems.length}',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 15,
                  color: _selectedNames.length == _trayItems.length
                      ? AppTheme.primaryTeal
                      : AppTheme.textSecondary,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Expanded(
          child: GridView.builder(
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 1.35,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: _selectionPool.length,
            itemBuilder: (ctx, idx) {
              final item = _selectionPool[idx];
              final isSelected = _selectedNames.contains(item.name);
              return GestureDetector(
                onTap: () => _toggleSelection(item.name),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isSelected ? AppTheme.tealSurface : Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isSelected ? AppTheme.primaryTeal : AppTheme.borderSubtle,
                      width: isSelected ? 2 : 1,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        item.icon,
                        color: isSelected ? AppTheme.primaryTeal : item.color,
                        size: 32,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        item.name,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                          fontSize: 14,
                          color: isSelected ? AppTheme.primaryTealDark : AppTheme.textPrimary,
                        ),
                      ),
                    ],
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
            onPressed: _selectedNames.isNotEmpty ? _finishGame : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryTeal,
              foregroundColor: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text(
              'Submit Choices',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
            ),
          ),
        ),
      ],
    );
  }
}
