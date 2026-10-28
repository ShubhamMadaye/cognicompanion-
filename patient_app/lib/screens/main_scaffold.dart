import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/localization_provider.dart';
import '../core/providers/patient_provider.dart';
import 'home_screen.dart';
import 'memories_screen.dart';
import 'profile_screen.dart';
import '../games/games_overview_screen.dart';

class MainScaffold extends StatefulWidget {
  const MainScaffold({super.key});

  @override
  State<MainScaffold> createState() => _MainScaffoldState();
}

class _MainScaffoldState extends State<MainScaffold> with WidgetsBindingObserver {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Ensure polling is active when scaffold mounts
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<PatientProvider>().startPolling();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!mounted) return;
    final patientProvider = context.read<PatientProvider>();
    if (state == AppLifecycleState.resumed) {
      // Immediate silent refresh on coming back to foreground
      patientProvider.silentSync();
      patientProvider.startPolling();
    } else if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      patientProvider.stopPolling();
    }
  }

  final List<Widget> _pages = const [
    HomeScreen(),
    GamesOverviewScreen(),
    MemoriesScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppTheme.surfaceCard,
          border: Border(
            top: BorderSide(color: AppTheme.borderStone, width: 1),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (i) => setState(() => _currentIndex = i),
          backgroundColor: AppTheme.surfaceCard,
          elevation: 0,
          selectedItemColor: AppTheme.primaryTeal,
          unselectedItemColor: AppTheme.textSecondary,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
          unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 12),
          type: BottomNavigationBarType.fixed,
          items: [
            BottomNavigationBarItem(
              icon: const Icon(Icons.home_outlined),
              activeIcon: const Icon(Icons.home_rounded),
              label: l.tr('nav_home'),
            ),
            BottomNavigationBarItem(
              icon: const Icon(Icons.psychology_outlined),
              activeIcon: const Icon(Icons.psychology_rounded),
              label: l.tr('nav_games'),
            ),
            BottomNavigationBarItem(
              icon: const Icon(Icons.photo_album_outlined),
              activeIcon: const Icon(Icons.photo_album_rounded),
              label: l.tr('nav_memories'),
            ),
            BottomNavigationBarItem(
              icon: const Icon(Icons.person_outline_rounded),
              activeIcon: const Icon(Icons.person_rounded),
              label: l.tr('nav_profile'),
            ),
          ],
        ),
      ),
    );
  }
}
