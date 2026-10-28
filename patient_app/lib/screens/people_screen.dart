import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/localization_provider.dart';
import '../core/providers/patient_provider.dart';
import '../services/api_service.dart';
import 'voice_chat_screen.dart';

class PeopleScreen extends StatefulWidget {
  const PeopleScreen({super.key});

  @override
  State<PeopleScreen> createState() => _PeopleScreenState();
}

class _PeopleScreenState extends State<PeopleScreen> {
  List<Map<String, dynamic>> _livePeople = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetchPeople());
  }

  Future<void> _fetchPeople() async {
    final patientId = context.read<PatientProvider>().profile.id;
    if (patientId.isEmpty) return;
    setState(() => _isLoading = true);
    try {
      final people = await ApiService.fetchPeople(patientId: patientId);
      if (mounted && people.isNotEmpty) {
        setState(() {
          _livePeople = people.map((p) {
            final name = (p['full_name'] ?? p['name'] ?? 'Family').toString();
            final relationship = (p['relationship'] ?? 'Care Circle').toString();
            return {
              'name': name,
              'relationship': relationship,
              'initial': name.isNotEmpty ? name[0].toUpperCase() : 'P',
              'phone': p['phone_number'] ?? p['phone'],
              'color': AppTheme.primaryTeal,
            };
          }).toList();
        });
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded,
              color: AppTheme.textPrimary, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(l.tr('people'),
            style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary)),
        backgroundColor: AppTheme.background,
        elevation: 0,
      ),
      body: _isLoading && _livePeople.isEmpty
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryTeal))
          : RefreshIndicator(
              color: AppTheme.primaryTeal,
              onRefresh: _fetchPeople,
              child: _livePeople.isEmpty
                  ? Center(
                      child: Text(
                        'No care circle members registered yet.',
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                      ),
                    )
                  : GridView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 12,
                        mainAxisSpacing: 12,
                        childAspectRatio: 0.80,
                      ),
                      itemCount: _livePeople.length,
                      itemBuilder: (context, index) {
                        final person = _livePeople[index];
                        return _buildPersonCard(context, person, l);
                      },
                    ),
            ),
    );
  }

  Widget _buildPersonCard(BuildContext context, Map<String, dynamic> person,
      LocalizationProvider l) {
    final accentColor = person['color'] as Color? ?? AppTheme.primaryTeal;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderStone, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        children: [
          // Monogram Portrait Avatar
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accentColor.withValues(alpha: 0.1),
              border: Border.all(
                color: accentColor.withValues(alpha: 0.3),
                width: 1.5,
              ),
            ),
            child: Center(
              child: Text(
                person['initial'] as String,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: accentColor,
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            person['name'],
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: const Color(0xFFF7F5F0),
              borderRadius: BorderRadius.circular(5),
              border: Border.all(color: const Color(0xFFE8E4DC)),
            ),
            child: Text(
              l.tr(person['relationKey'] as String),
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
          const Spacer(),
          // "Talk about Person" button
          GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const VoiceChatScreen()),
              );
            },
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFFAF8F5),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE2DDD5)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.mic_rounded,
                      color: AppTheme.primaryTeal, size: 15),
                  const SizedBox(width: 5),
                  Text(
                    'Ask About ${person['name']}',
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppTheme.primaryTeal,
                      fontWeight: FontWeight.w700,
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
