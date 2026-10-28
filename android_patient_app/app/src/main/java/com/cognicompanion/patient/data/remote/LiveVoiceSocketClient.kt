package com.cognicompanion.patient.data.remote

import android.util.Log
import com.cognicompanion.patient.BuildConfig
import com.squareup.moshi.Moshi
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.*
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

sealed class LiveVoiceEvent {
    data class SessionReady(val message: String, val capabilities: List<String>) : LiveVoiceEvent()
    data object UserSpeaking : LiveVoiceEvent()
    data class UserTranscript(val transcript: String) : LiveVoiceEvent()
    data class Processing(val message: String) : LiveVoiceEvent()
    data class AssistantReply(
        val text: String,
        val intent: String?,
        val confidence: Double?,
        val sources: List<String>,
        val conversationId: String?
    ) : LiveVoiceEvent()
    data class AudioChunk(val audioBase64: String) : LiveVoiceEvent()
    data object TurnFinished : LiveVoiceEvent()
    data class Interrupted(val reason: String) : LiveVoiceEvent()
    data class Error(val message: String, val code: String?) : LiveVoiceEvent()
    data object Disconnected : LiveVoiceEvent()
}

enum class LiveSocketState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    LISTENING,
    PROCESSING,
    SPEAKING,
    ERROR
}

@Singleton
class LiveVoiceSocketClient @Inject constructor(
    private val tokenStore: TokenStore,
    private val moshi: Moshi
) {
    companion object {
        private const val TAG = "LiveVoiceSocket"
    }

    private val client: OkHttpClient = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _state = MutableStateFlow(LiveSocketState.DISCONNECTED)
    val state: StateFlow<LiveSocketState> = _state.asStateFlow()

    private val _events = MutableSharedFlow<LiveVoiceEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<LiveVoiceEvent> = _events.asSharedFlow()

    fun connect(patientId: String, languageCode: String) {
        disconnect()

        scope.launch {
            _state.value = LiveSocketState.CONNECTING
            val baseUrl = tokenStore.getBaseUrl() ?: BuildConfig.BASE_URL
            val wsUrl = baseUrl
                .replace("http://", "ws://")
                .replace("https://", "wss://")
                .trimEnd('/') + "/voice/live"

            Log.d(TAG, "Connecting to WebSocket: $wsUrl")

            val request = Request.Builder()
                .url(wsUrl)
                .build()

            webSocket = client.newWebSocket(request, object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    Log.d(TAG, "WebSocket connected successfully.")
                    _state.value = LiveSocketState.CONNECTED

                    // Send START_SESSION payload
                    val startSessionJson = JSONObject().apply {
                        put("type", "START_SESSION")
                        put("patient_id", patientId)
                        put("language_code", languageCode)
                    }
                    webSocket.send(startSessionJson.toString())
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    handleTextMessage(text)
                }

                override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                    // Optional binary reception if server transmits raw audio bytes
                }

                override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                    Log.d(TAG, "WebSocket closing: $code / $reason")
                    _state.value = LiveSocketState.DISCONNECTED
                    _events.tryEmit(LiveVoiceEvent.Disconnected)
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    Log.e(TAG, "WebSocket error: ${t.message}", t)
                    _state.value = LiveSocketState.ERROR
                    _events.tryEmit(LiveVoiceEvent.Error(t.message ?: "Connection failed", null))
                }
            })
        }
    }

    private fun handleTextMessage(text: String) {
        try {
            val json = JSONObject(text)
            val type = json.optString("type")

            when (type) {
                "SESSION_READY" -> {
                    _state.value = LiveSocketState.LISTENING
                    val capabilities = mutableListOf<String>()
                    json.optJSONArray("capabilities")?.let { arr ->
                        for (i in 0 until arr.length()) capabilities.add(arr.getString(i))
                    }
                    _events.tryEmit(LiveVoiceEvent.SessionReady(
                        message = json.optString("message"),
                        capabilities = capabilities
                    ))
                }
                "USER_SPEAKING" -> {
                    _events.tryEmit(LiveVoiceEvent.UserSpeaking)
                }
                "USER_TRANSCRIPT" -> {
                    _events.tryEmit(LiveVoiceEvent.UserTranscript(json.optString("transcript")))
                }
                "PROCESSING" -> {
                    _state.value = LiveSocketState.PROCESSING
                    _events.tryEmit(LiveVoiceEvent.Processing(json.optString("message", "Processing...")))
                }
                "ASSISTANT_REPLY" -> {
                    _state.value = LiveSocketState.SPEAKING
                    val sources = mutableListOf<String>()
                    json.optJSONArray("sources")?.let { arr ->
                        for (i in 0 until arr.length()) {
                            val src = arr.optJSONObject(i)
                            sources.add(src?.optString("title") ?: "")
                        }
                    }
                    _events.tryEmit(LiveVoiceEvent.AssistantReply(
                        text = json.optString("text"),
                        intent = json.optString("intent", null),
                        confidence = if (json.has("confidence")) json.optDouble("confidence") else null,
                        sources = sources,
                        conversationId = json.optString("conversation_id", null)
                    ))
                }
                "AUDIO_CHUNK" -> {
                    _events.tryEmit(LiveVoiceEvent.AudioChunk(json.optString("audio_base64")))
                }
                "TURN_FINISHED" -> {
                    _state.value = LiveSocketState.LISTENING
                    _events.tryEmit(LiveVoiceEvent.TurnFinished)
                }
                "INTERRUPTED" -> {
                    _state.value = LiveSocketState.LISTENING
                    _events.tryEmit(LiveVoiceEvent.Interrupted(json.optString("reason", "Interrupted")))
                }
                "ERROR" -> {
                    _events.tryEmit(LiveVoiceEvent.Error(
                        message = json.optString("message", "Unknown error"),
                        code = json.optString("code", null)
                    ))
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing server message: ${e.message}", e)
        }
    }

    /**
     * Stream a raw 16kHz PCM audio chunk to the backend VAD.
     */
    fun sendPcmChunk(pcmBytes: ByteArray, offset: Int = 0, length: Int = pcmBytes.size) {
        val socket = webSocket ?: return
        if (_state.value != LiveSocketState.DISCONNECTED && _state.value != LiveSocketState.CONNECTING) {
            val byteString = pcmBytes.toByteString(offset, length)
            socket.send(byteString)
        }
    }

    /**
     * Trigger immediate client-side barge-in interruption.
     * Halts assistant playback on server and transitions state back to listening.
     */
    fun sendBargeInInterrupt() {
        val socket = webSocket ?: return
        val json = JSONObject().apply {
            put("type", "BARGE_IN_INTERRUPT")
        }
        socket.send(json.toString())
        _state.value = LiveSocketState.LISTENING
    }

    fun disconnect() {
        try {
            webSocket?.close(1000, "Normal closure")
        } catch (_: Exception) {}
        webSocket = null
        _state.value = LiveSocketState.DISCONNECTED
    }
}
