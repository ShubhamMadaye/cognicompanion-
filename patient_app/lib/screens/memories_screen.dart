import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/localization_provider.dart';
import '../core/providers/patient_provider.dart';
import '../services/api_service.dart';
import '../services/voice_service.dart';
import 'people_screen.dart';

class MemoriesScreen extends StatefulWidget {
  const MemoriesScreen({super.key});

  @override
  State<MemoriesScreen> createState() => _MemoriesScreenState();
}

class _MemoriesScreenState extends State<MemoriesScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final VoiceService _voiceService = VoiceService();
  String? _currentlySpeakingMemoryTitle;
  List<Map<String, dynamic>> _liveMemories = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _voiceService.init();
    _voiceService.isSpeakingNotifier.addListener(_onTtsStateChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetchLiveMemories());
  }

  Future<void> _fetchLiveMemories() async {
    final patientId = context.read<PatientProvider>().profile.id;
    if (patientId.isEmpty) return;
    setState(() => _isLoading = true);
    try {
      final items = await ApiService.fetchMemories(patientId: patientId);
      if (mounted && items.isNotEmpty) {
        setState(() {
          _liveMemories = items.map((m) {
            final who = (m['person_name'] ?? m['who'] ?? 'Family').toString();
            final relationship = (m['relationship'] ?? 'Loved One').toString();
            final title = (m['title'] ?? 'Care Memory').toString();
            final subtitle = (m['description'] ?? m['subtitle'] ?? '').toString();
            final timeStr = (m['event_date'] ?? m['time'] ?? 'Recently').toString();
            return {
              'who': who,
              'relationship': relationship,
              'title': title,
              'subtitle': subtitle,
              'time': timeStr,
              'tags': (m['tags'] as List<dynamic>?)?.map((t) => t.toString()).toList() ?? ['Memory'],
              'isSignificant': m['is_significant'] == true || m['isSignificant'] == true,
              'icon': Icons.photo_library_outlined,
              'color': AppTheme.primaryTeal,
              'initial': who.isNotEmpty ? who[0].toUpperCase() : 'M',
            };
          }).toList();
        });
      }
    } catch (_) {
      // Keep existing list or fallback
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _onTtsStateChanged() {
    if (!mounted) return;
    if (!_voiceService.isSpeakingNotifier.value) {
      if (_currentlySpeakingMemoryTitle != null) {
        setState(() => _currentlySpeakingMemoryTitle = null);
      }
    }
  }

  @override
  void dispose() {
    _voiceService.isSpeakingNotifier.removeListener(_onTtsStateChanged);
    _voiceService.stop();
    _tabController.dispose();
    super.dispose();
  }

  void _toggleStorySpeech(Map<String, dynamic> mem) async {
    HapticFeedback.lightImpact();
    final title = mem['title'] as String;

    if (_currentlySpeakingMemoryTitle == title) {
      await _voiceService.stop();
      if (mounted) {
        setState(() => _currentlySpeakingMemoryTitle = null);
      }
    } else {
      await _voiceService.stop();
      if (mounted) {
        setState(() => _currentlySpeakingMemoryTitle = title);
      }
      final narrative =
          "${mem['who']}, your ${mem['relationship']}. ${mem['title']}. ${mem['subtitle']}. Recorded on ${mem['time']}.";
      await _voiceService.speak(narrative);
    }
  }

  // Memory entries with clear WHO -> WHAT -> WHEN structure
  static const List<Map<String, dynamic>> _memories = [
    {
      'who': 'Rahul',
      'relationship': 'Son',
      'title': "Rahul's Afternoon Visit",
      'subtitle':
          'Rahul came over with sweet mangoes. You both sat on the veranda enjoying tea and reminiscing about the garden.',
      'time': 'Yesterday at 3:30 PM',
      'tags': ['Family Visit', 'Tea Time'],
      'isSignificant': true,
      'icon': Icons.family_restroom_rounded,
      'color': AppTheme.primaryTeal,
      'initial': 'R',
    },
    {
      'who': 'Priya & Family',
      'relationship': 'Daughter & Grandchildren',
      'title': 'Sunday Family Lunch',
      'subtitle':
          'Priya and the kids brought lunch. Everyone sat around the dining table, laughed together, and looked at old albums.',
      'time': 'Sunday at 1:00 PM',
      'tags': ['Family Gathering', 'Lunch'],
      'isSignificant': true,
      'icon': Icons.restaurant_rounded,
      'color': Color(0xFFB45309), // Warm Amber
      'initial': 'P',
    },
    {
      'who': 'Dr. Sharma',
      'relationship': 'Family Physician',
      'title': 'Routine Wellness Checkup',
      'subtitle':
          'Dr. Sharma checked your blood pressure and heart rate. Everything looks steady and well controlled.',
      'time': '2 days ago at 11:00 AM',
      'tags': ['Health & Checkup'],
      'isSignificant': false,
      'icon': Icons.health_and_safety_outlined,
      'color': Color(0xFF15803D), // Emerald
      'initial': 'D',
    },
    {
      'who': 'Anita',
      'relationship': 'Sister',
      'title': "Evening Phone Call with Anita",
      'subtitle':
          'Anita called to ask about your week and shared memories about childhood holidays in Shimla.',
      'time': '3 days ago at 6:15 PM',
      'tags': ['Phone Call', 'Family'],
      'isSignificant': false,
      'icon': Icons.phone_in_talk_rounded,
      'color': Color(0xFF184E5A),
      'initial': 'A',
    },
  ];

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ──────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    l.tr('my_memories'),
                    style: AppTheme.headingLarge,
                  ),
                  // People button
                  GestureDetector(
                    onTap: () {
                      HapticFeedback.selectionClick();
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const PeopleScreen(),
                        ),
                      );
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryTealLight,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: AppTheme.primaryTeal.withValues(alpha: 0.25),
                        ),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.people_alt_rounded,
                              color: AppTheme.primaryTealDark, size: 18),
                          const SizedBox(width: 6),
                          Text(
                            l.tr('people'),
                            style: const TextStyle(
                              color: AppTheme.primaryTealDark,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // ── Tab bar ──────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.04),
                      blurRadius: 8,
                    ),
                  ],
                ),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    color: AppTheme.primaryTeal,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  indicatorSize: TabBarIndicatorSize.tab,
                  indicatorPadding: const EdgeInsets.all(4),
                  labelColor: Colors.white,
                  unselectedLabelColor: AppTheme.textSecondary,
                  labelStyle: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                  unselectedLabelStyle: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                  ),
                  tabs: [
                    Tab(text: l.tr('tab_today')),
                    Tab(text: l.tr('tab_this_week')),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // ── Memory list (WHO -> WHAT -> WHEN) ────────────────────────
            Expanded(
              child: RefreshIndicator(
                color: AppTheme.primaryTeal,
                onRefresh: _fetchLiveMemories,
                child: _isLoading && _liveMemories.isEmpty
                    ? const Center(
                        child: CircularProgressIndicator(color: AppTheme.primaryTeal),
                      )
                    : TabBarView(
                        controller: _tabController,
                        children: [
                          _buildMemoryList(
                            (_liveMemories.isNotEmpty ? _liveMemories : _memories).take(2).toList(),
                          ),
                          _buildMemoryList(
                            _liveMemories.isNotEmpty ? _liveMemories : _memories,
                          ),
                        ],
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMemoryList(List<Map<String, dynamic>> items) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 16),
      itemBuilder: (context, index) {
        final mem = items[index];
        return _buildStructuredMemoryCard(mem);
      },
    );
  }

  Widget _buildStructuredMemoryCard(Map<String, dynamic> mem) {
    final isPlaying = _currentlySpeakingMemoryTitle == mem['title'];

    return Container(
      decoration: AppTheme.cardDecoration,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── 1. WHO: Person + Relationship ────────────────────────────────
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: (mem['color'] as Color? ?? AppTheme.primaryTeal)
                      .withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: (mem['color'] as Color? ?? AppTheme.primaryTeal)
                        .withValues(alpha: 0.25),
                  ),
                ),
                child: Center(
                  child: Icon(
                    mem['icon'] as IconData? ?? Icons.photo_library_outlined,
                    color: mem['color'] as Color? ?? AppTheme.primaryTeal,
                    size: 22,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          mem['who'] as String,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                        if (mem['isSignificant'] == true) ...[
                          const SizedBox(width: 6),
                          const Icon(
                            Icons.favorite_rounded,
                            color: AppTheme.gentleRose,
                            size: 15,
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 2),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF7F5F0),
                        borderRadius: BorderRadius.circular(5),
                        border: Border.all(color: const Color(0xFFE8E4DC)),
                      ),
                      child: Text(
                        mem['relationship'] as String,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // ── 2. WHAT: Event & Narrative Context ───────────────────────────
          Text(
            mem['title'] as String,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w800,
              color: AppTheme.textPrimary,
              height: 1.3,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            mem['subtitle'] as String,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: Color(0xFF44403C), // Stone 700
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),

          // ── 3. WHEN: Date & Time ─────────────────────────────────────────
          Row(
            children: [
              const Icon(
                Icons.access_time_rounded,
                size: 14,
                color: AppTheme.textSecondary,
              ),
              const SizedBox(width: 6),
              Text(
                mem['time'] as String,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // ── Action: [ Hear the story ] ───────────────────────────────────
          GestureDetector(
            onTap: () => _toggleStorySpeech(mem),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: isPlaying ? AppTheme.warmAmber : const Color(0xFFFAF8F5),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: isPlaying
                      ? AppTheme.warmAmber
                      : const Color(0xFFE2DDD5),
                  width: 1.2,
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    isPlaying
                        ? Icons.stop_circle_rounded
                        : Icons.volume_up_rounded,
                    color: isPlaying ? Colors.white : AppTheme.primaryTeal,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    isPlaying ? 'Stop listening' : 'Hear memory narrated',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: isPlaying ? Colors.white : AppTheme.primaryTeal,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
