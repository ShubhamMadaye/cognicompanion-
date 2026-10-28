package com.cognicompanion.patient.ui.voice

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.util.Base64
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.model.AskAssistantResponse
import com.cognicompanion.patient.data.model.SupportedLanguage
import com.cognicompanion.patient.data.model.VoiceConverseResponse
import com.cognicompanion.patient.data.remote.LiveSocketState
import com.cognicompanion.patient.data.remote.LiveVoiceEvent
import com.cognicompanion.patient.data.remote.LiveVoiceSocketClient
import com.cognicompanion.patient.data.remote.TokenStore
import com.cognicompanion.patient.data.repository.Result
import com.cognicompanion.patient.data.repository.VoiceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.inject.Inject

/** Conversation turn stored in local chat list */
data class ChatMessage(
    val id: String,
    val role: String,          // "user" | "assistant"
    val text: String,
    val grounded: Boolean = true,
    val intent: String? = null,
    val sources: List<String> = emptyList()
)

enum class VoiceState {
    Idle,           // ready to record
    Recording,      // mic is live
    Processing,     // sent to server, awaiting reply
    Speaking,       // playing assistant speech
    Error           // last operation failed
}

data class VoiceUiState(
    val voiceState: VoiceState = VoiceState.Idle,
    val messages: List<ChatMessage> = emptyList(),
    val typedInput: String = "",
    val errorMessage: String? = null,
    val isOffline: Boolean = false,
    val currentLanguage: SupportedLanguage = SupportedLanguage.ENGLISH,
    val conversationId: String? = null,
    val micPermissionGranted: Boolean = false,
    /** True if current language has voice (STT/TTS) support */
    val voiceSupported: Boolean = true,
    /** Phase 2: continuous streaming hands-free mode */
    val continuousVoice: Boolean = false,
    val isAssistantSpeaking: Boolean = false,
    val liveSocketState: LiveSocketState = LiveSocketState.DISCONNECTED
)

@HiltViewModel
class VoiceViewModel @Inject constructor(
    private val voiceRepository: VoiceRepository,
    private val tokenStore: TokenStore,
    private val liveVoiceSocketClient: LiveVoiceSocketClient,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _uiState = MutableStateFlow(VoiceUiState())
    val uiState: StateFlow<VoiceUiState> = _uiState.asStateFlow()

    private var recordingJob: Job? = null
    private var streamingJob: Job? = null
    private var audioFile: File? = null
    private var mediaPlayer: MediaPlayer? = null

    init {
        // Observe language preference
        viewModelScope.launch {
            tokenStore.languageCodeFlow.collect { code ->
                val lang = SupportedLanguage.fromCode(code)
                _uiState.value = _uiState.value.copy(
                    currentLanguage = lang,
                    voiceSupported  = lang.voiceSupported
                )
            }
        }

        // Observe continuous voice toggle
        viewModelScope.launch {
            tokenStore.continuousVoiceFlow.collect { enabled ->
                _uiState.value = _uiState.value.copy(continuousVoice = enabled)
                if (enabled && _uiState.value.micPermissionGranted) {
                    startContinuousVoiceSession()
                } else if (!enabled) {
                    stopContinuousVoiceSession()
                }
            }
        }

        // Observe Phase 2 live socket state
        viewModelScope.launch {
            liveVoiceSocketClient.state.collect { socketState ->
                _uiState.value = _uiState.value.copy(liveSocketState = socketState)
            }
        }

        // Observe Phase 2 live socket events
        viewModelScope.launch {
            liveVoiceSocketClient.events.collect { event ->
                handleLiveSocketEvent(event)
            }
        }
    }

    fun onPermissionResult(granted: Boolean) {
        _uiState.value = _uiState.value.copy(micPermissionGranted = granted)
        if (!granted) {
            setError("Microphone permission is required for voice. You can still type below.")
            stopContinuousVoiceSession()
        } else if (_uiState.value.continuousVoice) {
            startContinuousVoiceSession()
        }
    }

    fun onTypedInputChange(value: String) {
        _uiState.value = _uiState.value.copy(typedInput = value, errorMessage = null)
    }

    // ── Phase 2: Live WebSocket & Continuous Streaming ────────────────────────

    private fun startContinuousVoiceSession() {
        viewModelScope.launch {
            val patientId = tokenStore.getPatientId() ?: return@launch
            val langCode = _uiState.value.currentLanguage.bcp47Code
            liveVoiceSocketClient.connect(patientId, langCode)
            startPcmAudioStreaming()
        }
    }

    private fun stopContinuousVoiceSession() {
        streamingJob?.cancel()
        streamingJob = null
        stopAudioPlayback()
        liveVoiceSocketClient.disconnect()
        _uiState.value = _uiState.value.copy(voiceState = VoiceState.Idle)
    }

    private fun startPcmAudioStreaming() {
        streamingJob?.cancel()
        streamingJob = viewModelScope.launch(Dispatchers.IO) {
            val sampleRate  = 16000
            val channelCfg  = AudioFormat.CHANNEL_IN_MONO
            val encoding    = AudioFormat.ENCODING_PCM_16BIT
            val bufferSize  = AudioRecord.getMinBufferSize(sampleRate, channelCfg, encoding)

            val recorder = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRate, channelCfg, encoding, bufferSize
            )
            val buffer = ByteArray(bufferSize)

            try {
                recorder.startRecording()
                while (isActive && _uiState.value.continuousVoice) {
                    val read = recorder.read(buffer, 0, buffer.size)
                    if (read > 0) {
                        liveVoiceSocketClient.sendPcmChunk(buffer, 0, read)
                    }
                }
            } catch (e: Exception) {
                // Handled gracefully if mic is busy
            } finally {
                try {
                    recorder.stop()
                    recorder.release()
                } catch (_: Exception) {}
            }
        }
    }

    private fun handleLiveSocketEvent(event: LiveVoiceEvent) {
        when (event) {
            is LiveVoiceEvent.UserSpeaking -> {
                // Automatic barge-in interruption if assistant was speaking
                if (_uiState.value.isAssistantSpeaking) {
                    bargeIn()
                }
                _uiState.value = _uiState.value.copy(voiceState = VoiceState.Recording)
            }
            is LiveVoiceEvent.UserTranscript -> {
                val messages = _uiState.value.messages.toMutableList()
                val lastIdx = messages.indexOfLast { it.role == "user" }
                if (lastIdx >= 0 && messages[lastIdx].text == "[Voice message]") {
                    messages[lastIdx] = messages[lastIdx].copy(text = event.transcript)
                } else {
                    messages.add(ChatMessage(id = randomId(), role = "user", text = event.transcript))
                }
                _uiState.value = _uiState.value.copy(messages = messages)
            }
            is LiveVoiceEvent.Processing -> {
                _uiState.value = _uiState.value.copy(voiceState = VoiceState.Processing)
            }
            is LiveVoiceEvent.AssistantReply -> {
                val messages = _uiState.value.messages.toMutableList()
                messages.add(ChatMessage(
                    id = randomId(),
                    role = "assistant",
                    text = event.text,
                    intent = event.intent,
                    sources = event.sources
                ))
                _uiState.value = _uiState.value.copy(
                    messages = messages,
                    conversationId = event.conversationId ?: _uiState.value.conversationId,
                    voiceState = VoiceState.Speaking
                )
            }
            is LiveVoiceEvent.AudioChunk -> {
                playAudioBase64(event.audioBase64)
            }
            is LiveVoiceEvent.TurnFinished -> {
                _uiState.value = _uiState.value.copy(
                    voiceState = if (_uiState.value.isAssistantSpeaking) VoiceState.Speaking else VoiceState.Idle
                )
            }
            is LiveVoiceEvent.Interrupted -> {
                stopAudioPlayback()
                _uiState.value = _uiState.value.copy(voiceState = VoiceState.Idle)
            }
            is LiveVoiceEvent.Error -> {
                setError(event.message)
            }
            else -> {}
        }
    }

    /**
     * User or VAD barge-in interruption:
     * Immediately stops local audio playback and instructs backend to halt synthesis.
     */
    fun bargeIn() {
        stopAudioPlayback()
        if (_uiState.value.continuousVoice) {
            liveVoiceSocketClient.sendBargeInInterrupt()
        }
    }

    // ── Audio Playback ────────────────────────────────────────────────────────

    private fun playAudioBase64(base64Audio: String) {
        if (base64Audio.isBlank()) return
        try {
            stopAudioPlayback()
            val audioBytes = Base64.decode(base64Audio, Base64.DEFAULT)
            val tempMp3 = File.createTempFile("live_tts_", ".mp3", context.cacheDir)
            tempMp3.writeBytes(audioBytes)

            mediaPlayer = MediaPlayer().apply {
                setDataSource(tempMp3.absolutePath)
                prepare()
                setOnCompletionListener {
                    _uiState.value = _uiState.value.copy(
                        isAssistantSpeaking = false,
                        voiceState = VoiceState.Idle
                    )
                    tempMp3.delete()
                }
                start()
            }
            _uiState.value = _uiState.value.copy(
                isAssistantSpeaking = true,
                voiceState = VoiceState.Speaking
            )
        } catch (e: Exception) {
            _uiState.value = _uiState.value.copy(
                isAssistantSpeaking = false,
                voiceState = VoiceState.Idle
            )
        }
    }

    fun stopAudioPlayback() {
        try {
            mediaPlayer?.let {
                if (it.isPlaying) it.stop()
                it.release()
            }
        } catch (_: Exception) {}
        mediaPlayer = null
        _uiState.value = _uiState.value.copy(isAssistantSpeaking = false)
    }

    // ── Text query ────────────────────────────────────────────────────────────

    fun sendTextMessage() {
        val text = _uiState.value.typedInput.trim()
        if (text.isBlank()) return

        stopAudioPlayback()
        _uiState.value = _uiState.value.copy(
            typedInput  = "",
            errorMessage = null,
            messages    = _uiState.value.messages + ChatMessage(
                id   = randomId(),
                role = "user",
                text = text
            ),
            voiceState = VoiceState.Processing
        )

        viewModelScope.launch {
            when (val result = voiceRepository.askAssistant(
                query          = text,
                conversationId = _uiState.value.conversationId
            )) {
                is Result.Success -> handleAssistantResponse(result.data)
                is Result.Error   -> setError(result.message, result.isOffline)
            }
        }
    }

    // ── Push-to-Talk Voice recording (Atomic REST Mode) ───────────────────────

    fun startRecording() {
        val state = _uiState.value
        if (!state.micPermissionGranted) {
            setError("Microphone permission is required.")
            return
        }
        if (!state.voiceSupported) {
            setError("Voice is not available for ${state.currentLanguage.displayName}. Please type your message.")
            return
        }
        if (state.voiceState == VoiceState.Recording) return

        stopAudioPlayback()
        _uiState.value = _uiState.value.copy(
            voiceState   = VoiceState.Recording,
            errorMessage = null
        )

        recordingJob = viewModelScope.launch(Dispatchers.IO) {
            audioFile = recordPcmToWav()
        }
    }

    fun stopRecordingAndSend() {
        if (_uiState.value.voiceState != VoiceState.Recording) return
        recordingJob?.cancel()
        recordingJob = null

        val file = audioFile ?: run {
            setError("Recording failed. Please try again.")
            return
        }

        _uiState.value = _uiState.value.copy(
            voiceState = VoiceState.Processing,
            messages   = _uiState.value.messages + ChatMessage(
                id   = randomId(),
                role = "user",
                text = "[Voice message]"
            )
        )

        viewModelScope.launch {
            when (val result = voiceRepository.voiceConverse(
                audioFile      = file,
                conversationId = _uiState.value.conversationId
            )) {
                is Result.Success -> handleVoiceResponse(result.data)
                is Result.Error   -> setError(result.message, result.isOffline)
            }
        }
    }

    fun cancelRecording() {
        recordingJob?.cancel()
        recordingJob = null
        audioFile?.delete()
        audioFile = null
        _uiState.value = _uiState.value.copy(voiceState = VoiceState.Idle)
    }

    // ── Response handlers ─────────────────────────────────────────────────────

    private fun handleAssistantResponse(response: AskAssistantResponse) {
        val reply = response.reply.ifBlank { response.answer }
        _uiState.value = _uiState.value.copy(
            voiceState     = VoiceState.Idle,
            conversationId = response.conversationId,
            messages       = _uiState.value.messages + ChatMessage(
                id       = randomId(),
                role     = "assistant",
                text     = reply,
                grounded = response.grounded,
                intent   = response.intent,
                sources  = response.sources.map { it.title }
            )
        )
    }

    private fun handleVoiceResponse(response: VoiceConverseResponse) {
        val messages = _uiState.value.messages.toMutableList()
        val lastUserIdx = messages.indexOfLast { it.role == "user" }
        if (lastUserIdx >= 0 && messages[lastUserIdx].text == "[Voice message]") {
            messages[lastUserIdx] = messages[lastUserIdx].copy(
                text = response.transcript.ifBlank { "[Voice message]" }
            )
        }
        val reply = response.reply.ifBlank { response.answer }
        messages.add(
            ChatMessage(
                id       = randomId(),
                role     = "assistant",
                text     = reply,
                grounded = response.grounded,
                intent   = response.intent,
                sources  = response.sources.map { it.title }
            )
        )
        _uiState.value = _uiState.value.copy(
            voiceState     = VoiceState.Idle,
            conversationId = response.conversationId,
            messages       = messages
        )

        // Synthesize spoken voice output
        response.audioBase64?.let { b64 ->
            playAudioBase64(b64)
        }
    }

    private fun setError(message: String, isOffline: Boolean = false) {
        _uiState.value = _uiState.value.copy(
            voiceState   = VoiceState.Idle,
            errorMessage = message,
            isOffline    = isOffline
        )
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(errorMessage = null, isOffline = false)
    }

    // ── PCM → WAV recording ──────────────────────────────────────────────────

    private suspend fun recordPcmToWav(): File = withContext(Dispatchers.IO) {
        val sampleRate  = 16000
        val channelCfg  = AudioFormat.CHANNEL_IN_MONO
        val encoding    = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize  = AudioRecord.getMinBufferSize(sampleRate, channelCfg, encoding)

        val recorder = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate, channelCfg, encoding, bufferSize
        )

        val pcmFile = File(context.cacheDir, "voice_${System.currentTimeMillis()}.wav")
        val buffer  = ShortArray(bufferSize)

        try {
            recorder.startRecording()
            FileOutputStream(pcmFile).use { fos ->
                writeWavHeader(fos, sampleRate, 1, 16)
                while (_uiState.value.voiceState == VoiceState.Recording) {
                    val read = recorder.read(buffer, 0, bufferSize)
                    if (read > 0) {
                        val bytes = ByteArray(read * 2)
                        ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().put(buffer, 0, read)
                        fos.write(bytes)
                    }
                }
            }
            updateWavHeader(pcmFile)
        } finally {
            recorder.stop()
            recorder.release()
        }
        pcmFile
    }

    private fun writeWavHeader(fos: FileOutputStream, sampleRate: Int, channels: Int, bitsPerSample: Int) {
        val byteRate = sampleRate * channels * bitsPerSample / 8
        val blockAlign = channels * bitsPerSample / 8
        fos.write(byteArrayOf(
            'R'.code.toByte(), 'I'.code.toByte(), 'F'.code.toByte(), 'F'.code.toByte(),
            0, 0, 0, 0,
            'W'.code.toByte(), 'A'.code.toByte(), 'V'.code.toByte(), 'E'.code.toByte(),
            'f'.code.toByte(), 'm'.code.toByte(), 't'.code.toByte(), ' '.code.toByte(),
            16, 0, 0, 0,
            1, 0,
            channels.toByte(), 0,
            (sampleRate and 0xff).toByte(), ((sampleRate shr 8) and 0xff).toByte(),
            ((sampleRate shr 16) and 0xff).toByte(), ((sampleRate shr 24) and 0xff).toByte(),
            (byteRate and 0xff).toByte(), ((byteRate shr 8) and 0xff).toByte(),
            ((byteRate shr 16) and 0xff).toByte(), ((byteRate shr 24) and 0xff).toByte(),
            blockAlign.toByte(), 0,
            bitsPerSample.toByte(), 0,
            'd'.code.toByte(), 'a'.code.toByte(), 't'.code.toByte(), 'a'.code.toByte(),
            0, 0, 0, 0
        ))
    }

    private fun updateWavHeader(file: File) {
        val size = file.length()
        val dataSize = size - 44
        val fileSize = size - 8
        file.outputStream().use { out ->
            file.inputStream().use { inp ->
                val buf = inp.readBytes()
                val bb = ByteBuffer.wrap(buf).order(ByteOrder.LITTLE_ENDIAN)
                bb.putInt(4, fileSize.toInt())
                bb.putInt(40, dataSize.toInt())
                out.write(buf)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        stopAudioPlayback()
        stopContinuousVoiceSession()
    }

    private fun randomId() = System.currentTimeMillis().toString() + (0..999).random()
}
