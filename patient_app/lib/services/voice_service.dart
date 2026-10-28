import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class VoiceService {
  static final VoiceService _instance = VoiceService._internal();
  factory VoiceService() => _instance;
  VoiceService._internal();

  final FlutterTts _flutterTts = FlutterTts();
  final stt.SpeechToText _speech = stt.SpeechToText();

  bool _isTtsInitialized = false;
  bool _isSttInitialized = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  String _currentLanguage = "en-IN";

  final ValueNotifier<bool> isSpeakingNotifier = ValueNotifier<bool>(false);
  final ValueNotifier<bool> isListeningNotifier = ValueNotifier<bool>(false);
  VoidCallback? onSpeechCompleted;

  bool get isListening => _isListening;
  bool get isSpeaking => _isSpeaking;
  bool get isSttAvailable => _isSttInitialized && _speech.isAvailable;

  /// Initialize TTS with resilient platform fallback
  Future<void> init({String languageCode = "en-IN"}) async {
    try {
      _currentLanguage = languageCode;

      // Platform specific audio configuration
      if (!kIsWeb && defaultTargetPlatform == TargetPlatform.iOS) {
        await _flutterTts.setIosAudioCategory(
          IosTextToSpeechAudioCategory.playback,
          [
            IosTextToSpeechAudioCategoryOptions.defaultToSpeaker,
            IosTextToSpeechAudioCategoryOptions.allowBluetooth,
            IosTextToSpeechAudioCategoryOptions.allowBluetoothA2DP,
          ],
        );
      }

      await _flutterTts.awaitSpeakCompletion(true);
      await _flutterTts.setSpeechRate(0.46); // Compassionate, slower pace for elderly
      await _flutterTts.setVolume(1.0);
      await _flutterTts.setPitch(1.0);

      // Verify and set language with fallback
      await _configureTtsLanguage(languageCode);

      _flutterTts.setStartHandler(() {
        _isSpeaking = true;
        isSpeakingNotifier.value = true;
      });

      _flutterTts.setCompletionHandler(() {
        _isSpeaking = false;
        isSpeakingNotifier.value = false;
        onSpeechCompleted?.call();
      });

      _flutterTts.setCancelHandler(() {
        _isSpeaking = false;
        isSpeakingNotifier.value = false;
      });

      _flutterTts.setErrorHandler((msg) {
        _isSpeaking = false;
        isSpeakingNotifier.value = false;
        debugPrint("[VoiceService] TTS Error: $msg");
      });

      _isTtsInitialized = true;
      debugPrint("[VoiceService] TTS initialized successfully with language $_currentLanguage");
    } catch (e) {
      debugPrint("[VoiceService] TTS init error: $e");
    }
  }

  /// Configure TTS language with intelligent fallback
  Future<void> _configureTtsLanguage(String requestedLang) async {
    try {
      final dynamic rawLanguages = await _flutterTts.getLanguages;
      if (rawLanguages is List && rawLanguages.isNotEmpty) {
        final List<String> available = rawLanguages.map((e) => e.toString()).toList();

        // Exact match
        if (available.contains(requestedLang)) {
          await _flutterTts.setLanguage(requestedLang);
          return;
        }

        // Match with hyphen vs underscore (e.g. en_IN vs en-IN)
        final alternate = requestedLang.contains('-')
            ? requestedLang.replaceAll('-', '_')
            : requestedLang.replaceAll('_', '-');
        if (available.contains(alternate)) {
          await _flutterTts.setLanguage(alternate);
          return;
        }

        // Language family fallback (e.g. any en_* for en-IN, or any hi_* for hi)
        final prefix = requestedLang.split(RegExp(r'[-_]'))[0].toLowerCase();
        final familyMatch = available.firstWhere(
          (l) => l.toLowerCase().startsWith(prefix),
          orElse: () => '',
        );

        if (familyMatch.isNotEmpty) {
          await _flutterTts.setLanguage(familyMatch);
          return;
        }

        // Default to English or first available
        final enFallback = available.firstWhere(
          (l) => l.toLowerCase().startsWith('en'),
          orElse: () => available.first,
        );
        await _flutterTts.setLanguage(enFallback);
        return;
      }

      // Default
      await _flutterTts.setLanguage("en-US");
    } catch (e) {
      debugPrint("[VoiceService] Error setting TTS language: $e");
      try {
        await _flutterTts.setLanguage("en-US");
      } catch (_) {}
    }
  }

  /// Change TTS Language dynamically
  Future<void> setLanguage(String languageCode) async {
    _currentLanguage = languageCode;
    if (_isTtsInitialized) {
      await _configureTtsLanguage(languageCode);
    }
  }

  /// Speaks text aloud using device TTS
  Future<void> speak(String text, {String? languageCode}) async {
    if (text.trim().isEmpty) return;
    if (!_isTtsInitialized) await init(languageCode: languageCode ?? _currentLanguage);

    try {
      if (_isSpeaking) {
        await stop();
        // Give native audio engine a small window to release audio track
        await Future.delayed(const Duration(milliseconds: 60));
      }

      if (languageCode != null && languageCode != _currentLanguage) {
        await setLanguage(languageCode);
      }

      _isSpeaking = true;
      isSpeakingNotifier.value = true;
      await _flutterTts.speak(text);
    } catch (e) {
      _isSpeaking = false;
      isSpeakingNotifier.value = false;
      debugPrint("[VoiceService] TTS speak error: $e");
    }
  }

  /// Stops current speech output
  Future<void> stop() async {
    try {
      await _flutterTts.stop();
    } catch (_) {}
    _isSpeaking = false;
    isSpeakingNotifier.value = false;
  }

  /// Starts listening to microphone audio with partial preview and final confirmation
  Future<bool> startListening({
    required Function(String recognizedWords, bool isFinal) onResult,
    required Function(bool isListening) onStatusChange,
    String? languageCode,
  }) async {
    try {
      // If already speaking, stop first so mic doesn't record the assistant's voice
      if (_isSpeaking) {
        await stop();
      }

      if (!_isSttInitialized) {
        _isSttInitialized = await _speech.initialize(
          onStatus: (status) {
            final active = (status == 'listening');
            _isListening = active;
            isListeningNotifier.value = active;
            onStatusChange(active);
            debugPrint("[VoiceService] STT status: $status");
          },
          onError: (errorNotification) {
            _isListening = false;
            isListeningNotifier.value = false;
            onStatusChange(false);
            debugPrint("[VoiceService] STT error: ${errorNotification.errorMsg}");
          },
          debugLogging: false,
        );
      }

      if (_isSttInitialized && _speech.isAvailable) {
        final localeId = languageCode ?? _currentLanguage.replaceAll('-', '_');

        await _speech.listen(
          onResult: (result) {
            // Send live words + finalResult flag to caller
            onResult(result.recognizedWords, result.finalResult);
          },
          listenOptions: stt.SpeechListenOptions(
            listenMode: stt.ListenMode.dictation,
            cancelOnError: false,
            partialResults: true,
            localeId: localeId,
            pauseFor: const Duration(seconds: 3), // Generous pause time for elderly pauses
            listenFor: const Duration(seconds: 30),
          ),
        );

        _isListening = true;
        isListeningNotifier.value = true;
        onStatusChange(true);
        return true;
      }
    } catch (e) {
      debugPrint("[VoiceService] STT start error: $e");
    }

    _isListening = false;
    isListeningNotifier.value = false;
    onStatusChange(false);
    return false;
  }

  /// Stops listening to microphone
  Future<void> stopListening() async {
    try {
      if (_speech.isListening) {
        await _speech.stop();
      }
    } catch (_) {}
    _isListening = false;
    isListeningNotifier.value = false;
  }
}
