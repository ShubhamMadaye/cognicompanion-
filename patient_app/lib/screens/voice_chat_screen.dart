import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/localization_provider.dart';
import '../core/providers/patient_provider.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/voice_service.dart';
import '../services/live_voice_socket_service.dart';

enum VoiceLifecycleState {
  idle,
  listening,
  processing,
  speaking,
  error,
}

class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key});

  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

class _VoiceChatScreenState extends State<VoiceChatScreen>
    with TickerProviderStateMixin {
  VoiceLifecycleState _state = VoiceLifecycleState.idle;
  String? _activeConversationId;
  String _liveTranscription = '';
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _textController = TextEditingController();
  final VoiceService _voiceService = VoiceService();
  final LiveVoiceSocketService _liveSocket = LiveVoiceSocketService();
  int _selectedTab = 2; // Default to 2 (Live Voice) for hands-free mode

  // Multimodal Image Attachment
  File? _selectedImage;
  String? _selectedImageBase64;
  final ImagePicker _picker = ImagePicker();

  // Animation Controllers
  late AnimationController _breathController;
  late Animation<double> _breathAnimation;

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  late AnimationController _speakingController;

  // Messages
  List<VoiceChatMessage>? _messages;

  List<VoiceChatMessage> _getMessages(LocalizationProvider l) {
    _messages ??= [
      VoiceChatMessage(
        text: l.tr('initial_greeting'),
        isUser: false,
        timestamp: DateTime.now().subtract(const Duration(minutes: 1)),
      ),
    ];
    return _messages!;
  }

  List<String> _getSuggestions(LocalizationProvider l) => [
        l.tr('suggestion_1'),
        l.tr('suggestion_2'),
        l.tr('suggestion_3'),
        l.tr('suggestion_4'),
      ];

  String _getBcp47Locale(String locale) {
    switch (locale) {
      case 'hi':
        return 'hi-IN';
      case 'mr':
        return 'mr-IN';
      case 'bn':
        return 'bn-IN';
      case 'ta':
        return 'ta-IN';
      case 'te':
        return 'te-IN';
      case 'kn':
        return 'kn-IN';
      case 'gu':
        return 'gu-IN';
      case 'pa':
        return 'pa-IN';
      case 'ml':
        return 'ml-IN';
      case 'as':
        return 'as-IN';
      case 'ne':
        return 'ne-NP';
      case 'brx':
        return 'brx-IN';
      case 'mni':
        return 'mni-IN';
      case 'lus':
        return 'lus-IN';
      case 'kha':
        return 'kha-IN';
      case 'grt':
        return 'grt-IN';
      case 'trp':
        return 'trp-IN';
      case 'nag':
        return 'nag-IN';
      case 'njz':
        return 'njz-IN';
      case 'pbv':
        return 'pbv-IN';
      default:
        return 'en-IN';
    }
  }

  @override
  void initState() {
    super.initState();
    _voiceService.init();

    // 1. Breathing animation for IDLE & PROCESSING
    _breathController = AnimationController(
      duration: const Duration(milliseconds: 2200),
      vsync: this,
    )..repeat(reverse: true);
    _breathAnimation = Tween<double>(begin: 1.0, end: 1.06).animate(
      CurvedAnimation(parent: _breathController, curve: Curves.easeInOut),
    );

    // 2. Strong pulse for LISTENING
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1300),
      vsync: this,
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // 3. Audio bars animation for SPEAKING
    _speakingController = AnimationController(
      duration: const Duration(milliseconds: 650),
      vsync: this,
    )..repeat(reverse: true);

    // Real TTS lifecycle listener
    _voiceService.isSpeakingNotifier.addListener(_onSpeakingChanged);

    // Continuous voice loop: when assistant finishes speaking, listen automatically if in Voice tab
    _voiceService.onSpeechCompleted = () {
      if (!mounted) return;
      if (_selectedTab == 2 && _state != VoiceLifecycleState.processing) {
        Future.delayed(const Duration(milliseconds: 550), () {
          if (mounted && _selectedTab == 2 && _state != VoiceLifecycleState.processing) {
            _startContinuousListening();
          }
        });
      }
    };

    // Real-time live voice socket callbacks
    _liveSocket.onBargeIn = () {
      if (!mounted) return;
      debugPrint('[VoiceChatScreen] Barge-in triggered! Halting audio.');
      _voiceService.stop();
      if (_state == VoiceLifecycleState.speaking) {
        setState(() => _state = VoiceLifecycleState.listening);
      }
    };

    _liveSocket.onUserTranscript = (text) {
      if (!mounted) return;
      setState(() => _liveTranscription = text);
    };

    _liveSocket.onAssistantReply = (text, intent, sources) {
      if (!mounted) return;
      final reply = VoiceChatMessage(
        text: text,
        isUser: false,
        timestamp: DateTime.now(),
        intent: intent,
        confidence: 0.95,
        sources: sources,
      );
      final l = context.read<LocalizationProvider>();
      final messages = _getMessages(l);
      setState(() {
        _latestSpokenText = text;
        messages.add(reply);
        _state = VoiceLifecycleState.speaking;
      });
      _scrollToBottom();
      _voiceService.speak(text, languageCode: _getBcp47Locale(l.locale));
    };

    _liveSocket.onTurnFinished = () {
      if (!mounted) return;
      if (_selectedTab == 2 && _state != VoiceLifecycleState.processing) {
        Future.delayed(const Duration(milliseconds: 550), () {
          if (mounted && _selectedTab == 2 && _state != VoiceLifecycleState.processing) {
            _startContinuousListening();
          }
        });
      }
    };

    // Auto-connect socket & greet patient
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final l = context.read<LocalizationProvider>();
      final patientId = context.read<PatientProvider>().profile.id;
      _liveSocket.connect(
        patientId: patientId,
        languageCode: _getBcp47Locale(l.locale),
      );
      Future.delayed(const Duration(milliseconds: 500), () {
        if (!mounted) return;
        final greeting = l.tr('initial_greeting');
        _voiceService.speak(greeting, languageCode: _getBcp47Locale(l.locale));
      });
    });
  }

  void _onSpeakingChanged() {
    if (!mounted) return;
    final speaking = _voiceService.isSpeakingNotifier.value;
    if (speaking) {
      if (_state != VoiceLifecycleState.speaking) {
        setState(() => _state = VoiceLifecycleState.speaking);
      }
    } else {
      if (_state == VoiceLifecycleState.speaking) {
        setState(() => _state = VoiceLifecycleState.idle);
      }
    }
  }

  @override
  void dispose() {
    _liveSocket.disconnect();
    _voiceService.onSpeechCompleted = null;
    _voiceService.isSpeakingNotifier.removeListener(_onSpeakingChanged);
    _voiceService.stop();
    _voiceService.stopListening();
    _scrollController.dispose();
    _textController.dispose();
    _breathController.dispose();
    _pulseController.dispose();
    _speakingController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  String _latestSpokenText = '';

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      if (picked != null) {
        final bytes = await picked.readAsBytes();
        setState(() {
          _selectedImage = File(picked.path);
          _selectedImageBase64 = base64Encode(bytes);
          // Switch to chat mode so the user sees the attached photo preview and chat bubble
          _selectedTab = 0;
        });
      }
    } catch (e) {
      debugPrint('[VoiceChatScreen] Image pick error: $e');
    }
  }

  void _clearSelectedImage() {
    setState(() {
      _selectedImage = null;
      _selectedImageBase64 = null;
    });
  }

  void _handleQuery(
    String query,
    List<VoiceChatMessage> messages,
    LocalizationProvider l, {
    String? imagePath,
    String? imageBase64,
  }) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty && imageBase64 == null) return;
    if (_state == VoiceLifecycleState.processing) return;
    HapticFeedback.lightImpact();

    final activePatientId = context.read<PatientProvider>().profile.id;

    await _voiceService.stop();
    await _voiceService.stopListening();

    final userText = trimmed.isNotEmpty ? trimmed : 'What is in this picture?';

    setState(() {
      _liveTranscription = '';
      _state = VoiceLifecycleState.processing;
      messages.add(VoiceChatMessage(
        text: userText,
        isUser: true,
        timestamp: DateTime.now(),
        imagePath: imagePath,
        imageBase64: imageBase64,
      ));
    });
    _scrollToBottom();

    // Use real-time WebSocket if connected
    if (_liveSocket.isConnected) {
      _liveSocket.sendQuery(
        userText,
        imageBase64: imageBase64,
        languageCode: _getBcp47Locale(l.locale),
      );
      return;
    }

    try {
      final reply = await ApiService.askAssistant(
        patientId: activePatientId,
        query: userText,
        conversationId: _activeConversationId,
        languageCode: l.locale,
        imageBase64: imageBase64,
      );

      if (!mounted) return;

      if (reply.conversationId != null) {
        _activeConversationId = reply.conversationId;
      }

      setState(() {
        _latestSpokenText = reply.text;
        messages.add(reply);
      });
      _scrollToBottom();

      await _voiceService.speak(
        reply.text,
        languageCode: _getBcp47Locale(l.locale),
      );
    } catch (e) {
      if (mounted) {
        setState(() => _state = VoiceLifecycleState.error);
      }
    }
  }

  void _enterVoiceMode(List<VoiceChatMessage> messages, LocalizationProvider l) async {
    final patientId = context.read<PatientProvider>().profile.id;
    await _voiceService.stop();
    await _voiceService.stopListening();
    if (!mounted) return;
    setState(() {
      _selectedTab = 2;
      _state = VoiceLifecycleState.idle;
    });

    if (!_liveSocket.isConnected) {
      _liveSocket.connect(
        patientId: patientId,
        languageCode: _getBcp47Locale(l.locale),
      );
    }

    final prompt = l.locale == 'hi'
        ? 'ध्वनि मोड सक्रिय है। मैं आपकी बात सुन रहा हूँ, पूछिए।'
        : l.locale == 'mr'
            ? 'आवाज मोड सुरू आहे. मी ऐकत आहे, विचारा.'
            : 'Voice mode active. I am listening, go ahead and ask me anything.';

    setState(() {
      _latestSpokenText = prompt;
    });

    await _voiceService.speak(prompt, languageCode: _getBcp47Locale(l.locale));

    Future.delayed(const Duration(milliseconds: 2800), () {
      if (mounted && _selectedTab == 2 && _state == VoiceLifecycleState.idle) {
        _startContinuousListening();
      }
    });
  }

  Future<void> _startContinuousListening() async {
    if (!mounted || _state == VoiceLifecycleState.processing || _state == VoiceLifecycleState.listening) {
      return;
    }

    final l = context.read<LocalizationProvider>();
    final messages = _getMessages(l);

    await _voiceService.stop();
    setState(() {
      _liveTranscription = '';
      _state = VoiceLifecycleState.listening;
    });

    final started = await _voiceService.startListening(
      onResult: (words, isFinal) {
        if (mounted) {
          setState(() => _liveTranscription = words);
        }
        if (isFinal && words.trim().isNotEmpty) {
          final query = words.trim();
          _liveTranscription = '';
          _handleQuery(query, messages, l);
        }
      },
      onStatusChange: (listening) {
        if (mounted) {
          if (listening && _state != VoiceLifecycleState.processing) {
            setState(() => _state = VoiceLifecycleState.listening);
          } else if (!listening && _state == VoiceLifecycleState.listening) {
            if (_liveTranscription.trim().isNotEmpty) {
              final query = _liveTranscription.trim();
              _liveTranscription = '';
              _handleQuery(query, messages, l);
            } else {
              setState(() => _state = VoiceLifecycleState.idle);
            }
          }
        }
      },
      languageCode: _getBcp47Locale(l.locale),
    );

    if (!started && mounted) {
      setState(() => _state = VoiceLifecycleState.idle);
    }
  }

  void _onOrbTap(
    List<VoiceChatMessage> messages,
    List<String> suggestions,
    LocalizationProvider l,
  ) async {
    HapticFeedback.lightImpact();

    switch (_state) {
      case VoiceLifecycleState.speaking:
        // Immediate barge-in interruption: cut off speaker & server task
        _liveSocket.sendBargeIn();
        await _voiceService.stop();
        if (mounted) {
          if (_selectedTab == 2) {
            _startContinuousListening();
          } else {
            setState(() => _state = VoiceLifecycleState.idle);
          }
        }
        break;

      case VoiceLifecycleState.listening:
        await _voiceService.stopListening();
        if (_liveTranscription.trim().isNotEmpty) {
          final query = _liveTranscription.trim();
          _liveTranscription = '';
          _handleQuery(query, messages, l);
        } else {
          if (mounted) setState(() => _state = VoiceLifecycleState.idle);
        }
        break;

      case VoiceLifecycleState.processing:
        break;

      case VoiceLifecycleState.error:
      case VoiceLifecycleState.idle:
        await _voiceService.stop();
        setState(() {
          _liveTranscription = '';
          _state = VoiceLifecycleState.listening;
        });

        final started = await _voiceService.startListening(
          onResult: (words, isFinal) {
            if (mounted) {
              setState(() => _liveTranscription = words);
            }
            if (isFinal && words.trim().isNotEmpty) {
              final query = words.trim();
              _liveTranscription = '';
              _handleQuery(query, messages, l);
            }
          },
          onStatusChange: (listening) {
            if (mounted) {
              if (listening && _state != VoiceLifecycleState.processing) {
                setState(() => _state = VoiceLifecycleState.listening);
              } else if (!listening && _state == VoiceLifecycleState.listening) {
                if (_liveTranscription.trim().isNotEmpty) {
                  final query = _liveTranscription.trim();
                  _liveTranscription = '';
                  _handleQuery(query, messages, l);
                } else {
                  setState(() => _state = VoiceLifecycleState.idle);
                }
              }
            }
          },
          languageCode: _getBcp47Locale(l.locale),
        );

        if (!started && mounted) {
          setState(() => _state = VoiceLifecycleState.idle);
        }
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = context.watch<LocalizationProvider>();
    final messages = _getMessages(l);
    final suggestions = _getSuggestions(l);

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppTheme.textPrimary, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          l.tr('voice_assistant'),
          style: AppTheme.headingMedium.copyWith(fontSize: 20),
        ),
        actions: [
          IconButton(
            tooltip: 'Camera / Visual Question',
            icon: const Icon(Icons.photo_camera_rounded, color: AppTheme.primaryTeal),
            onPressed: () => _pickImage(ImageSource.camera),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // ── Mode Switcher Tabs (Anti-Vibecoding Semantic Navigation) ───
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                children: [
                  _tabChip(2, Icons.mic_rounded, 'Live Voice', messages, l),
                  const SizedBox(width: 8),
                  _tabChip(0, Icons.chat_bubble_outline_rounded, 'Chat & Photos', messages, l),
                  const SizedBox(width: 8),
                  _tabChip(1, Icons.lightbulb_outline_rounded, 'Prompts', messages, l),
                ],
              ),
            ),

            // ── Main Body: Dedicated Live Voice vs Conversational Chat ──────
            Expanded(
              child: _selectedTab == 2
                  ? _buildFullVoiceModeView(messages, suggestions, l)
                  : _buildChatStreamView(messages, suggestions, l),
            ),

            // ── Bottom Input Bar: Only active in Chat / Prompts mode ────────
            if (_selectedTab != 2)
              _buildBottomInputBar(messages, l),
          ],
        ),
      ),
    );
  }

  /// ── Dedicated Full-Screen Live Voice View ─────────────────────────────────
  Widget _buildFullVoiceModeView(
    List<VoiceChatMessage> messages,
    List<String> suggestions,
    LocalizationProvider l,
  ) {
    final isListening = _state == VoiceLifecycleState.listening;
    final isProcessing = _state == VoiceLifecycleState.processing;
    final isSpeaking = _state == VoiceLifecycleState.speaking;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const SizedBox(height: 20),

          // Large Animated Voice Orb
          _buildLargeVoiceOrb(messages, suggestions, l),

          const SizedBox(height: 24),

          // Clear State Header
          _buildStateLabel(l),

          const SizedBox(height: 20),

          // Real-Time Visual Feedback Card (Calm, High-Contrast Stone Card)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isListening
                    ? AppTheme.primaryTeal
                    : isSpeaking
                        ? AppTheme.primaryTealDark
                        : isProcessing
                            ? AppTheme.warmAmber
                            : AppTheme.borderSubtle,
                width: 1.2,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.03),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isListening
                            ? AppTheme.primaryTeal
                            : isSpeaking
                                ? AppTheme.gentleGreen
                                : isProcessing
                                    ? AppTheme.warmAmber
                                    : AppTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      isListening
                          ? 'LISTENING TO YOU'
                          : isProcessing
                              ? 'SEARCHING CARE RECORDS & MEMORIES...'
                              : isSpeaking
                                  ? 'SPEAKING ALOUD'
                                  : 'VOICE MODE READY',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.6,
                        color: isListening
                            ? AppTheme.primaryTeal
                            : isSpeaking
                                ? AppTheme.gentleGreen
                                : isProcessing
                                    ? AppTheme.warmAmber
                                    : AppTheme.textSecondary,
                      ),
                    ),
                    const Spacer(),
                    const Icon(Icons.volume_up_rounded, size: 18, color: AppTheme.primaryTeal),
                  ],
                ),
                const SizedBox(height: 12),

                if (isListening) ...[
                  Text(
                    _liveTranscription.isNotEmpty
                        ? '"$_liveTranscription"'
                        : 'Listening... Speak your question anytime.',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: _liveTranscription.isNotEmpty ? FontWeight.w700 : FontWeight.w500,
                      fontStyle: _liveTranscription.isNotEmpty ? FontStyle.italic : FontStyle.normal,
                      color: _liveTranscription.isNotEmpty ? AppTheme.textPrimary : AppTheme.textSecondary,
                      height: 1.4,
                    ),
                  ),
                ] else if (isProcessing) ...[
                  const Row(
                    children: [
                      SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5, color: AppTheme.warmAmber),
                      ),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Retrieving personal memories, medication schedule & routines...',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppTheme.warmAmber),
                        ),
                      ),
                    ],
                  ),
                ] else if (isSpeaking) ...[
                  Text(
                    _latestSpokenText.isNotEmpty ? '"$_latestSpokenText"' : 'Speaking response...',
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.primaryTealDark,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 14),
                  // Prominent Barge-in Button
                  Align(
                    alignment: Alignment.centerRight,
                    child: ElevatedButton.icon(
                      onPressed: () {
                        HapticFeedback.heavyImpact();
                        _liveSocket.sendBargeIn();
                        _voiceService.stop();
                        _startContinuousListening();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.warmAmber,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      icon: const Icon(Icons.back_hand_rounded, size: 18),
                      label: const Text('Interrupt / Speak Now', style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                  ),
                ] else ...[
                  const Text(
                    'Hands-free continuous conversation active.\nTap the microphone circle or speak anytime.',
                    style: TextStyle(
                      fontSize: 15,
                      color: AppTheme.textSecondary,
                      height: 1.4,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(height: 28),

          // Switch to Chat History Button
          OutlinedButton.icon(
            onPressed: () {
              HapticFeedback.lightImpact();
              setState(() => _selectedTab = 0);
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.primaryTeal,
              side: const BorderSide(color: AppTheme.primaryTeal),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            icon: const Icon(Icons.chat_bubble_outline_rounded, size: 18),
            label: const Text('View Full Chat History & Photos', style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  /// ── Conversational Chat Stream View ───────────────────────────────────────
  Widget _buildChatStreamView(
    List<VoiceChatMessage> messages,
    List<String> suggestions,
    LocalizationProvider l,
  ) {
    return Column(
      children: [
        if (_selectedTab == 1)
          _buildSuggestionsChips(suggestions, messages, l),

        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            itemCount: messages.length + (_state == VoiceLifecycleState.processing ? 1 : 0),
            itemBuilder: (context, index) {
              if (index < messages.length) {
                return _buildBubble(messages[index], l);
              }
              return _buildThinkingIndicator();
            },
          ),
        ),
      ],
    );
  }

  Widget _buildLargeVoiceOrb(
    List<VoiceChatMessage> messages,
    List<String> suggestions,
    LocalizationProvider l,
  ) {
    final scaleAnimation = _state == VoiceLifecycleState.listening
        ? _pulseAnimation
        : (_state == VoiceLifecycleState.processing || _state == VoiceLifecycleState.idle)
            ? _breathAnimation
            : const AlwaysStoppedAnimation(1.0);

    return GestureDetector(
      onTap: () => _onOrbTap(messages, suggestions, l),
      child: AnimatedBuilder(
        animation: scaleAnimation,
        builder: (context, child) {
          final scale = scaleAnimation.value;

          return Transform.scale(
            scale: scale,
            child: Stack(
              alignment: Alignment.center,
              children: [
                if (_state == VoiceLifecycleState.listening) ...[
                  Container(
                    width: 196,
                    height: 196,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: AppTheme.primaryTeal.withValues(alpha: 0.22),
                        width: 1.5,
                      ),
                    ),
                  ),
                  Container(
                    width: 168,
                    height: 168,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: AppTheme.primaryTeal.withValues(alpha: 0.4),
                        width: 1.5,
                      ),
                    ),
                  ),
                ],
                Container(
                  width: 140,
                  height: 140,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _getOrbColor(),
                    border: Border.all(
                      color: const Color(0xFFE8E4DC),
                      width: 2.0,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Center(
                    child: _getOrbCenterContent(),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Color _getOrbColor() {
    switch (_state) {
      case VoiceLifecycleState.idle:
        return AppTheme.primaryTeal;
      case VoiceLifecycleState.listening:
        return AppTheme.primaryTealDark;
      case VoiceLifecycleState.processing:
        return AppTheme.warmAmber;
      case VoiceLifecycleState.speaking:
        return AppTheme.primaryTeal;
      case VoiceLifecycleState.error:
        return AppTheme.gentleRose;
    }
  }

  Widget _getOrbCenterContent() {
    switch (_state) {
      case VoiceLifecycleState.idle:
        return const Icon(Icons.mic, color: Colors.white, size: 58);
      case VoiceLifecycleState.listening:
        return const Icon(Icons.graphic_eq_rounded, color: Colors.white, size: 58);
      case VoiceLifecycleState.processing:
        return const Icon(Icons.hourglass_empty_rounded, color: Colors.white, size: 52);
      case VoiceLifecycleState.speaking:
        return AnimatedBuilder(
          animation: _speakingController,
          builder: (context, _) {
            final val = _speakingController.value;
            return Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                _audioBar(18 + (val * 20)),
                const SizedBox(width: 6),
                _audioBar(34 - (val * 16)),
                const SizedBox(width: 6),
                _audioBar(22 + (val * 22)),
              ],
            );
          },
        );
      case VoiceLifecycleState.error:
        return const Icon(Icons.refresh_rounded, color: Colors.white, size: 54);
    }
  }

  Widget _audioBar(double height) {
    return Container(
      width: 6,
      height: height.clamp(12.0, 44.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }

  Widget _buildStateLabel(LocalizationProvider l) {
    final String title;
    final String subtitle;
    final Color titleColor;

    switch (_state) {
      case VoiceLifecycleState.idle:
        title = l.tr('tap_to_talk');
        subtitle = l.tr('here_to_help');
        titleColor = AppTheme.textPrimary;
        break;
      case VoiceLifecycleState.listening:
        title = l.tr('listening');
        subtitle = l.tr('tap_to_finish');
        titleColor = AppTheme.primaryTeal;
        break;
      case VoiceLifecycleState.processing:
        title = l.tr('thinking');
        subtitle = l.tr('searching_memory');
        titleColor = AppTheme.warmAmber;
        break;
      case VoiceLifecycleState.speaking:
        title = l.tr('speaking');
        subtitle = l.tr('tap_to_pause');
        titleColor = AppTheme.primaryTealDark;
        break;
      case VoiceLifecycleState.error:
        title = l.tr('error_title');
        subtitle = l.tr('error_subtitle');
        titleColor = AppTheme.gentleRose;
        break;
    }

    return Column(
      children: [
        Text(
          title,
          style: AppTheme.headingMedium.copyWith(
            color: titleColor,
            fontSize: 22,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: AppTheme.secondaryText.copyWith(fontSize: 14),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _tabChip(int idx, IconData icon, String label, List<VoiceChatMessage> messages, LocalizationProvider l) {
    final selected = _selectedTab == idx;
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedTab = idx);
        if (idx == 2) {
          _enterVoiceMode(messages, l);
        } else {
          _voiceService.stop();
          _voiceService.stopListening();
          setState(() => _state = VoiceLifecycleState.idle);
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primaryTeal : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected ? AppTheme.primaryTeal : AppTheme.borderSubtle,
            width: 1.0,
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 4,
                    offset: const Offset(0, 1),
                  )
                ]
              : [],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color: selected ? Colors.white : AppTheme.textSecondary,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : AppTheme.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionsChips(
    List<String> suggestions,
    List<VoiceChatMessage> messages,
    LocalizationProvider l,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        children: suggestions
            .map(
              (s) => ActionChip(
                backgroundColor: Colors.white,
                side: const BorderSide(color: AppTheme.borderSubtle),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                label: Text(
                  s,
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppTheme.primaryTeal,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                onPressed: () => _handleQuery(s, messages, l),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _buildBubble(VoiceChatMessage msg, LocalizationProvider l) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: msg.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!msg.isUser) ...[
            Container(
              width: 32,
              height: 32,
              margin: const EdgeInsets.only(right: 8, bottom: 4),
              decoration: BoxDecoration(
                color: AppTheme.primaryTeal,
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFFE8E4DC), width: 1),
              ),
              child: const Icon(Icons.support_agent_rounded, color: Colors.white, size: 18),
            ),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
              decoration: BoxDecoration(
                color: msg.isUser ? AppTheme.primaryTeal : Colors.white,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(14),
                  topRight: const Radius.circular(14),
                  bottomLeft: Radius.circular(msg.isUser ? 14 : 3),
                  bottomRight: Radius.circular(msg.isUser ? 3 : 14),
                ),
                border: Border.all(
                  color: msg.isUser ? AppTheme.primaryTeal : AppTheme.borderSubtle,
                  width: 1.0,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.02),
                    blurRadius: 4,
                    offset: const Offset(0, 1),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Multimodal Attached Photo
                  if (msg.imagePath != null && File(msg.imagePath!).existsSync()) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.file(
                        File(msg.imagePath!),
                        width: 200,
                        height: 150,
                        fit: BoxFit.cover,
                      ),
                    ),
                    const SizedBox(height: 8),
                  ] else if (msg.imageBase64 != null) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.memory(
                        base64Decode(msg.imageBase64!),
                        width: 200,
                        height: 150,
                        fit: BoxFit.cover,
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],

                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          msg.text,
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w500,
                            height: 1.45,
                            color: msg.isUser ? Colors.white : AppTheme.textPrimary,
                          ),
                        ),
                      ),
                      if (!msg.isUser) ...[
                        const SizedBox(width: 8),
                        GestureDetector(
                          onTap: () {
                            HapticFeedback.lightImpact();
                            _voiceService.speak(
                              msg.text,
                              languageCode: _getBcp47Locale(l.locale),
                            );
                          },
                          child: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              color: AppTheme.primaryTealLight,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Icon(
                              Icons.volume_up_rounded,
                              size: 18,
                              color: AppTheme.primaryTealDark,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),

                  // Grounded Sources tags
                  if (msg.sources != null && msg.sources!.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: msg.sources!
                          .take(2)
                          .map(
                            (s) => Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade100,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                s,
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.grey.shade700,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildThinkingIndicator() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14, left: 46),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) => _dot(i)),
        ),
      ),
    );
  }

  Widget _buildBottomInputBar(
    List<VoiceChatMessage> messages,
    LocalizationProvider l,
  ) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Attached Image Preview Strip
            if (_selectedImage != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: Colors.grey.shade50,
                child: Row(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.file(
                        _selectedImage!,
                        width: 48,
                        height: 48,
                        fit: BoxFit.cover,
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Photo attached for visual analysis',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20, color: Colors.grey),
                      onPressed: _clearSelectedImage,
                    ),
                  ],
                ),
              ),

            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  // Camera Button
                  IconButton(
                    icon: const Icon(Icons.camera_alt_rounded, color: AppTheme.primaryTeal),
                    onPressed: () => _pickImage(ImageSource.camera),
                  ),

                  // Gallery Button
                  IconButton(
                    icon: const Icon(Icons.photo_library_rounded, color: AppTheme.softBlue),
                    onPressed: () => _pickImage(ImageSource.gallery),
                  ),

                  // Text Field
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        color: AppTheme.background,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: TextField(
                        controller: _textController,
                        decoration: InputDecoration(
                          hintText: _selectedImage != null
                              ? 'Ask about this photo...'
                              : l.tr('type_question_hint'),
                          hintStyle: AppTheme.secondaryText.copyWith(fontSize: 14),
                          border: InputBorder.none,
                        ),
                        onSubmitted: (val) {
                          _submitText(messages, l);
                        },
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Send Button
                  Container(
                    decoration: const BoxDecoration(
                      color: AppTheme.primaryTeal,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                      onPressed: () => _submitText(messages, l),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _submitText(List<VoiceChatMessage> messages, LocalizationProvider l) {
    final val = _textController.text;
    final imgPath = _selectedImage?.path;
    final imgBase64 = _selectedImageBase64;

    if (val.trim().isNotEmpty || imgBase64 != null) {
      _textController.clear();
      _clearSelectedImage();
      _handleQuery(
        val,
        messages,
        l,
        imagePath: imgPath,
        imageBase64: imgBase64,
      );
    }
  }

  Widget _dot(int index) {
    return AnimatedBuilder(
      animation: _breathController,
      builder: (_, __) {
        final opacity = sin((_breathController.value * 2 * pi) + (index * pi / 3)).abs().clamp(0.25, 1.0);
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 3),
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppTheme.primaryTeal.withValues(alpha: opacity),
          ),
        );
      },
    );
  }
}
