import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'auth_service.dart';

/// Real-time bidirectional WebSocket service for streaming voice,
/// sub-second latency turn-taking, and instantaneous barge-in interruption.
class LiveVoiceSocketService {
  static final LiveVoiceSocketService _instance =
      LiveVoiceSocketService._internal();
  factory LiveVoiceSocketService() => _instance;
  LiveVoiceSocketService._internal();

  WebSocket? _socket;
  StreamSubscription? _subscription;
  bool _isConnected = false;
  String _currentState = 'IDLE';

  // Callbacks for live UI updates
  Function(String text)? onUserTranscript;
  Function(String text, String? intent, List<String>? sources)? onAssistantReply;
  Function(String audioBase64)? onAudioChunk;
  VoidCallback? onBargeIn;
  Function(String state)? onStateChanged;
  VoidCallback? onTurnFinished;

  bool get isConnected => _isConnected;
  String get currentState => _currentState;

  /// Derive the WebSocket URL from the active AuthService.baseUrl.
  static String get webSocketUrl {
    final base = AuthService.baseUrl;
    final wsScheme = base.startsWith('https://') ? 'wss://' : 'ws://';
    final hostAndPath = base.replaceAll(RegExp(r'^https?://'), '');
    return '$wsScheme$hostAndPath/voice/live';
  }

  /// Connect to the backend real-time voice streaming gateway.
  Future<bool> connect({
    String? patientId,
    String languageCode = 'en-IN',
  }) async {
    await disconnect();

    try {
      final uri = Uri.parse(webSocketUrl);
      debugPrint('[LiveVoiceSocket] Connecting to: $uri');

      _socket = await WebSocket.connect(uri.toString())
          .timeout(const Duration(seconds: 4));

      _isConnected = true;
      _currentState = 'CONNECTED';
      onStateChanged?.call(_currentState);

      _subscription = _socket!.listen(
        _onMessage,
        onError: (err) {
          debugPrint('[LiveVoiceSocket] Error: $err');
          _handleDisconnect();
        },
        onDone: () {
          debugPrint('[LiveVoiceSocket] Connection closed by server.');
          _handleDisconnect();
        },
        cancelOnError: false,
      );

      // Start the voice session with the patient context
      sendEvent({
        'type': 'START_SESSION',
        'patient_id': patientId,
        'language_code': languageCode,
      });

      return true;
    } catch (e) {
      debugPrint('[LiveVoiceSocket] Connection failed: $e');
      _handleDisconnect();
      return false;
    }
  }

  /// Disconnect cleanly.
  Future<void> disconnect() async {
    _isConnected = false;
    _currentState = 'IDLE';
    await _subscription?.cancel();
    _subscription = null;
    try {
      await _socket?.close();
    } catch (_) {}
    _socket = null;
  }

  /// Send a JSON control event over the WebSocket.
  void sendEvent(Map<String, dynamic> payload) {
    if (!_isConnected || _socket == null) return;
    try {
      _socket!.add(jsonEncode(payload));
    } catch (e) {
      debugPrint('[LiveVoiceSocket] Error sending event: $e');
    }
  }

  /// Send a binary PCM audio chunk to the backend.
  void sendAudioBytes(List<int> pcmBytes) {
    if (!_isConnected || _socket == null) return;
    try {
      _socket!.add(pcmBytes);
    } catch (e) {
      debugPrint('[LiveVoiceSocket] Error sending audio chunk: $e');
    }
  }

  /// Send a text query for instant PME memory RAG processing, optionally with visual image context.
  void sendQuery(String query, {String? imageBase64, String? languageCode}) {
    final payload = <String, dynamic>{
      'type': 'TEXT_QUERY',
      'query': query.trim(),
    };
    if (imageBase64 != null && imageBase64.isNotEmpty) {
      payload['image_base64'] = imageBase64;
    }
    if (languageCode != null && languageCode.isNotEmpty) {
      payload['language_code'] = languageCode;
    }
    sendEvent(payload);
  }

  /// Trigger an immediate client-side barge-in interruption.
  void sendBargeIn() {
    debugPrint('[LiveVoiceSocket] Client triggering barge-in interruption.');
    sendEvent({'type': 'BARGE_IN_INTERRUPT'});
    onBargeIn?.call();
  }

  void _onMessage(dynamic rawMessage) {
    if (rawMessage is! String) return;

    try {
      final Map<String, dynamic> data = jsonDecode(rawMessage);
      final eventType = data['type'] as String?;

      switch (eventType) {
        case 'SESSION_READY':
        case 'LISTENING':
          _currentState = 'LISTENING';
          onStateChanged?.call('LISTENING');
          break;

        case 'USER_SPEAKING':
          _currentState = 'LISTENING';
          onStateChanged?.call('LISTENING');
          break;

        case 'USER_TRANSCRIPT':
          final transcript = data['transcript'] as String?;
          if (transcript != null) {
            onUserTranscript?.call(transcript);
          }
          break;

        case 'PROCESSING':
          _currentState = 'PROCESSING';
          onStateChanged?.call('PROCESSING');
          break;

        case 'ASSISTANT_REPLY':
          _currentState = 'SPEAKING';
          onStateChanged?.call('SPEAKING');
          final text = data['text'] as String? ?? '';
          final intent = data['intent'] as String?;
          final rawSources = data['sources'] as List<dynamic>?;
          final sources = rawSources
              ?.map((s) => '${s['type'].toString().toUpperCase()}: ${s['title']}')
              .toList();

          onAssistantReply?.call(text, intent, sources);
          break;

        case 'AUDIO_CHUNK':
          final b64 = data['audio_base64'] as String?;
          if (b64 != null) {
            onAudioChunk?.call(b64);
          }
          break;

        case 'INTERRUPTED':
          debugPrint('[LiveVoiceSocket] Server confirmed interruption: ${data['reason']}');
          _currentState = 'LISTENING';
          onBargeIn?.call();
          onStateChanged?.call('LISTENING');
          break;

        case 'TURN_FINISHED':
          _currentState = 'LISTENING';
          onTurnFinished?.call();
          onStateChanged?.call('LISTENING');
          break;

        case 'ERROR':
          debugPrint('[LiveVoiceSocket] Server error: ${data['message']}');
          _currentState = 'LISTENING';
          onStateChanged?.call('LISTENING');
          break;
      }
    } catch (e) {
      debugPrint('[LiveVoiceSocket] Parse error: $e');
    }
  }

  void _handleDisconnect() {
    _isConnected = false;
    _currentState = 'DISCONNECTED';
    onStateChanged?.call(_currentState);
  }
}
