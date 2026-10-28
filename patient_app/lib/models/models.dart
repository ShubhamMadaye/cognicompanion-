class PatientProfile {
  final String id;
  final String fullName;
  final String preferredLanguage;
  final String emergencyPhone;
  final String emergencyName;

  PatientProfile({
    required this.id,
    required this.fullName,
    required this.preferredLanguage,
    required this.emergencyPhone,
    required this.emergencyName,
  });

  String get firstName => fullName.split(' ').first;
  String get emergencyFirstName => emergencyName.split(' ').first;

  factory PatientProfile.mock() {
    return PatientProfile(
      id: '00000000-0000-0000-0000-000000000001',
      fullName: 'Shanti Devi',
      preferredLanguage: 'Hindi / English',
      emergencyPhone: '+919876543210',
      emergencyName: 'Rahul',
    );
  }

  factory PatientProfile.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>? ?? {};
    return PatientProfile(
      id: json['id']?.toString() ?? '00000000-0000-0000-0000-000000000001',
      fullName: user['full_name']?.toString() ?? json['full_name']?.toString() ?? 'Shanti Devi',
      preferredLanguage: json['preferred_language']?.toString() ?? 'en',
      emergencyPhone: (json['emergency_contact_phone']?.toString() ?? '+919876543210')
          .replaceAll(RegExp(r'[\s\-()]'), ''),
      emergencyName: json['emergency_contact_name']?.toString() ?? 'Caregiver',
    );
  }

  PatientProfile copyWith({
    String? id,
    String? fullName,
    String? preferredLanguage,
    String? emergencyPhone,
    String? emergencyName,
  }) {
    return PatientProfile(
      id: id ?? this.id,
      fullName: fullName ?? this.fullName,
      preferredLanguage: preferredLanguage ?? this.preferredLanguage,
      emergencyPhone: emergencyPhone ?? this.emergencyPhone,
      emergencyName: emergencyName ?? this.emergencyName,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'full_name': fullName,
    'preferred_language': preferredLanguage,
    'emergency_contact_phone': emergencyPhone,
    'emergency_contact_name': emergencyName,
  };
}

class TimelineReminder {
  final String id;
  final String title;
  final String description;
  final String time;
  final String icon;
  final bool isCompleted;
  final bool isMedication;

  TimelineReminder({
    required this.id,
    required this.title,
    required this.description,
    required this.time,
    required this.icon,
    this.isCompleted = false,
    this.isMedication = false,
  });
}

class TodayTimelineItem {
  final String id;
  final String kind; // "medication", "routine", "memory", "event"
  final String title;
  final String subtitle;
  final String timeStr;
  final bool isCompleted;
  final bool isMedication;

  final String? takenAt;

  const TodayTimelineItem({
    required this.id,
    required this.kind,
    required this.title,
    required this.subtitle,
    required this.timeStr,
    this.isCompleted = false,
    this.isMedication = false,
    this.takenAt,
  });

  TodayTimelineItem copyWith({bool? isCompleted, String? takenAt}) {
    return TodayTimelineItem(
      id: id,
      kind: kind,
      title: title,
      subtitle: subtitle,
      timeStr: timeStr,
      isCompleted: isCompleted ?? this.isCompleted,
      isMedication: isMedication,
      takenAt: takenAt ?? this.takenAt,
    );
  }

  factory TodayTimelineItem.fromJson(Map<String, dynamic> json) {
    final metadata = json['metadata'] as Map<String, dynamic>? ?? {};
    final kind = json['kind']?.toString() ?? 'event';
    return TodayTimelineItem(
      id: json['id']?.toString() ?? json['title']?.toString() ?? 'item',
      kind: kind,
      title: json['title']?.toString() ?? '',
      subtitle: json['subtitle']?.toString() ?? '',
      timeStr: json['time_str']?.toString() ?? '',
      isMedication: kind == 'medication',
      isCompleted: metadata['taken'] == true || metadata['is_taken'] == true || metadata['is_completed'] == true || metadata['completed'] == true,
      takenAt: metadata['taken_at']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'kind': kind,
    'title': title,
    'subtitle': subtitle,
    'time_str': timeStr,
    'metadata': {
      'taken': isCompleted,
      'taken_at': takenAt,
    },
  };

  static List<TodayTimelineItem> mockItems() {
    return [
      const TodayTimelineItem(
        id: 'med-1', kind: 'medication',
        title: 'Vitamin B12',
        subtitle: '500mcg tablet — With breakfast',
        timeStr: '8:00 AM', isMedication: true,
      ),
      const TodayTimelineItem(
        id: 'routine-1', kind: 'routine',
        title: 'Morning Walk',
        subtitle: '20 minutes gentle walk in garden',
        timeStr: '9:00 AM',
      ),
      const TodayTimelineItem(
        id: 'med-2', kind: 'medication',
        title: 'Amlodipine',
        subtitle: '5mg — Blood pressure medication',
        timeStr: '10:00 AM', isMedication: true,
      ),
      const TodayTimelineItem(
        id: 'routine-2', kind: 'routine',
        title: 'Morning Prayers',
        subtitle: 'Quiet time for prayers and reflection',
        timeStr: '10:30 AM',
      ),
      const TodayTimelineItem(
        id: 'med-3', kind: 'medication',
        title: 'Calcium Tablet',
        subtitle: '500mg — With lunch',
        timeStr: '1:00 PM', isMedication: true,
      ),
      const TodayTimelineItem(
        id: 'routine-3', kind: 'routine',
        title: 'Afternoon Rest',
        subtitle: 'Short nap — up to 30 minutes',
        timeStr: '2:30 PM',
      ),
      const TodayTimelineItem(
        id: 'routine-4', kind: 'routine',
        title: 'Evening Tea Time',
        subtitle: 'Chai with light snack',
        timeStr: '5:00 PM',
      ),
    ];
  }
}

class VoiceChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final String? intent;
  final double? confidence;
  final List<String>? sources;
  final String? conversationId;
  final String? audioBase64;
  final String? imagePath;
  final String? imageBase64;

  VoiceChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.intent,
    this.confidence,
    this.sources,
    this.conversationId,
    this.audioBase64,
    this.imagePath,
    this.imageBase64,
  });
}
