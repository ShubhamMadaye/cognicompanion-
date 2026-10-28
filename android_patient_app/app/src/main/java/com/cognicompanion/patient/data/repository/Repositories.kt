package com.cognicompanion.patient.data.repository

import com.cognicompanion.patient.data.local.PendingMedLogDao
import com.cognicompanion.patient.data.local.TimelineCacheDao
import com.cognicompanion.patient.data.model.*
import com.cognicompanion.patient.data.remote.CogniCompanionApi
import com.cognicompanion.patient.data.remote.TokenStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

// ─────────────────────────────────────────────────────────────────────────────
// Result type
// ─────────────────────────────────────────────────────────────────────────────

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String, val code: Int? = null, val isOffline: Boolean = false) : Result<Nothing>()
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth Repository
// ─────────────────────────────────────────────────────────────────────────────

@Singleton
class AuthRepository @Inject constructor(
    private val api: CogniCompanionApi,
    private val tokenStore: TokenStore
) {
    suspend fun login(email: String, password: String): Result<TokenResponse> =
        withContext(Dispatchers.IO) {
            try {
                val response = api.login(LoginRequest(email, password))
                // ⚠️ Save token FIRST so OkHttp interceptor can attach it to follow-up calls
                tokenStore.saveNewAccessToken(response.accessToken)
                // Now fetch patient profile (requires Bearer token)
                val patient = api.getMyPatientProfile()
                tokenStore.saveSession(
                    accessToken  = response.accessToken,
                    refreshToken = response.refreshToken,
                    patientId    = patient.id,
                    userName     = response.user.fullName,
                    userEmail    = response.user.email
                )
                // Cache profile data for offline use
                tokenStore.saveProfileCache(
                    emergencyName  = patient.emergencyContactName,
                    emergencyPhone = patient.emergencyContactPhone,
                    dateOfBirth    = patient.dateOfBirth
                )
                Result.Success(response)
            } catch (e: retrofit2.HttpException) {
                val msg = when (e.code()) {
                    401  -> "Invalid email or password."
                    422  -> "Please enter a valid email address."
                    429  -> "Too many attempts. Please wait and try again."
                    else -> "Login failed (${e.code()})."
                }
                Result.Error(msg, e.code())
            } catch (e: java.io.IOException) {
                Result.Error("Cannot reach server. Check your network and server address.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "An unexpected error occurred.")
            }
        }

    suspend fun logout() {
        try { withContext(Dispatchers.IO) { api.logout() } } catch (_: Exception) {}
        tokenStore.clearSession()
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Patient / Dashboard Repository
// ─────────────────────────────────────────────────────────────────────────────

@Singleton
class PatientRepository @Inject constructor(
    private val api: CogniCompanionApi,
    private val tokenStore: TokenStore,
    private val timelineCacheDao: TimelineCacheDao,
    private val pendingMedLogDao: PendingMedLogDao,
    private val moshi: Moshi
) {
    private val metaType = Types.newParameterizedType(Map::class.java, String::class.java, Any::class.java)
    private val metaAdapter = moshi.adapter<Map<String, Any?>>(metaType)

    // ── Dashboard ─────────────────────────────────────────────────────────────

    suspend fun getDashboardSummary(): Result<DashboardSummaryResponse> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.getDashboardSummary(id))
            } catch (e: retrofit2.HttpException) {
                Result.Error("Server error: ${e.code()}", e.code())
            } catch (e: java.io.IOException) {
                Result.Error("No connection. Showing cached data.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Unknown error")
            }
        }

    // ── Timeline (with cache) ─────────────────────────────────────────────────

    suspend fun getTimeline(day: String? = null): Result<List<TimelineEntry>> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                val live = api.getTimeline(id, day)
                // Persist to cache
                timelineCacheDao.clearAll()
                timelineCacheDao.insertAll(live.map { it.toCacheEntity(metaAdapter) })
                Result.Success(live)
            } catch (e: java.io.IOException) {
                // Return cached version
                val cached = timelineCacheDao.getTimeline()
                if (cached.isNotEmpty()) {
                    Result.Success(cached.map { it.toTimelineEntry(metaAdapter) })
                } else {
                    Result.Error("No connection and no cached schedule.", isOffline = true)
                }
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load timeline")
            }
        }

    fun observeCachedTimeline(): Flow<List<CachedTimelineEntity>> =
        timelineCacheDao.observeTimeline()

    // ── Memories ─────────────────────────────────────────────────────────────

    suspend fun getMemories(): Result<List<MemoryListItem>> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.getMemories(id))
            } catch (e: java.io.IOException) {
                Result.Error("No connection.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load memories")
            }
        }

    suspend fun getPeople(): Result<List<PersonResponse>> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.getPeople(id))
            } catch (e: java.io.IOException) {
                Result.Error("No connection.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load people")
            }
        }

    // ── Medication Log (with offline outbox) ──────────────────────────────────

    suspend fun logMedication(medicationId: String, taken: Boolean, date: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                api.logMedication(id, medicationId, LogMedicationRequest(date, taken))
                Result.Success(Unit)
            } catch (e: java.io.IOException) {
                // Queue for later sync
                pendingMedLogDao.insert(
                    PendingMedicationLog(
                        localId      = UUID.randomUUID().toString(),
                        medicationId = medicationId,
                        logDate      = date,
                        taken        = taken
                    )
                )
                Result.Success(Unit)  // Optimistic — queued
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not log medication")
            }
        }

    /** Flush any pending offline medication logs. Call when connectivity returns. */
    suspend fun syncPendingMedLogs() = withContext(Dispatchers.IO) {
        val id = tokenStore.getPatientId() ?: return@withContext
        val pending = pendingMedLogDao.getAll()
        for (log in pending) {
            try {
                api.logMedication(id, log.medicationId, LogMedicationRequest(log.logDate, log.taken))
                pendingMedLogDao.delete(log)
            } catch (_: Exception) {
                break  // Stop on first failure; try again next time
            }
        }
    }

    fun pendingLogCount(): Flow<Int> = pendingMedLogDao.countPending()

    // ── Profile ───────────────────────────────────────────────────────────────

    suspend fun getMyProfile(): Result<PatientResponse> =
        withContext(Dispatchers.IO) {
            try {
                val result = api.getMyPatientProfile()
                // Refresh local cache
                tokenStore.saveProfileCache(
                    emergencyName  = result.emergencyContactName,
                    emergencyPhone = result.emergencyContactPhone,
                    dateOfBirth    = result.dateOfBirth
                )
                Result.Success(result)
            } catch (e: java.io.IOException) {
                Result.Error("No connection.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load profile")
            }
        }
}

// ─────────────────────────────────────────────────────────────────────────────
// Voice / Assistant Repository
// ─────────────────────────────────────────────────────────────────────────────

@Singleton
class VoiceRepository @Inject constructor(
    private val api: CogniCompanionApi,
    private val tokenStore: TokenStore
) {
    /** Send typed/text query to the AI assistant in the patient's selected language. */
    suspend fun askAssistant(
        query: String,
        conversationId: String? = null
    ): Result<AskAssistantResponse> = withContext(Dispatchers.IO) {
        try {
            val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
            val lang = tokenStore.getLanguageCode()
            val response = api.askAssistant(
                id,
                AskAssistantRequest(
                    query          = query,
                    conversationId = conversationId,
                    languageCode   = lang
                )
            )
            Result.Success(response)
        } catch (e: java.io.IOException) {
            Result.Error("No internet connection.", isOffline = true)
        } catch (e: Exception) {
            Result.Error(e.localizedMessage ?: "Assistant unavailable.")
        }
    }

    /**
     * Submit recorded audio for a full voice turn:
     * audio → STT → PME → LLM → TTS in selected language.
     */
    suspend fun voiceConverse(
        audioFile: File,
        conversationId: String? = null
    ): Result<VoiceConverseResponse> = withContext(Dispatchers.IO) {
        try {
            val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
            val lang = tokenStore.getLanguageCode()

            val audioPart = MultipartBody.Part.createFormData(
                name     = "audio",
                filename = audioFile.name,
                body     = audioFile.asRequestBody("audio/wav".toMediaType())
            )
            val langBody = lang.toRequestBody("text/plain".toMediaType())
            val convBody = conversationId?.toRequestBody("text/plain".toMediaType())

            val response = api.voiceConverse(id, audioPart, langBody, convBody)
            Result.Success(response)
        } catch (e: java.io.IOException) {
            Result.Error("No internet connection. Voice requires an active connection.", isOffline = true)
        } catch (e: retrofit2.HttpException) {
            when (e.code()) {
                400  -> Result.Error("Could not understand the audio. Please try again.")
                413  -> Result.Error("Audio recording is too long. Please keep it under 30 seconds.")
                else -> Result.Error("Voice service error (${e.code()}).")
            }
        } catch (e: Exception) {
            Result.Error("Voice assistant is currently unavailable. Please try again.")
        }
    }

    suspend fun listConversations(): Result<List<ConversationResponse>> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.listConversations(id))
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load conversations")
            }
        }
}

// ─────────────────────────────────────────────────────────────────────────────
// Games Repository
// ─────────────────────────────────────────────────────────────────────────────

@Singleton
class GamesRepository @Inject constructor(
    private val api: CogniCompanionApi,
    private val tokenStore: TokenStore
) {
    suspend fun listGames(): Result<List<GameResponse>> =
        withContext(Dispatchers.IO) {
            try {
                Result.Success(api.listGames())
            } catch (e: java.io.IOException) {
                Result.Error("No connection.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load games")
            }
        }

    suspend fun generateContent(gameType: String, difficulty: String = "MEDIUM"): Result<GameContentResponse> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.generateGameContent(id, gameType, difficulty))
            } catch (e: java.io.IOException) {
                Result.Error("No connection.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load game")
            }
        }

    suspend fun submitSession(request: CreateGameSessionRequest): Result<GameSessionResponse> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.recordGameSession(id, request))
            } catch (e: java.io.IOException) {
                Result.Error("Score not saved — no connection.", isOffline = true)
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not save session")
            }
        }

    suspend fun listSessions(): Result<List<GameSessionResponse>> =
        withContext(Dispatchers.IO) {
            try {
                val id = tokenStore.getPatientId() ?: return@withContext Result.Error("Not logged in.")
                Result.Success(api.listGameSessions(id))
            } catch (e: Exception) {
                Result.Error(e.localizedMessage ?: "Could not load history")
            }
        }
}

// ─────────────────────────────────────────────────────────────────────────────
// Room entity ↔ domain model conversions
// ─────────────────────────────────────────────────────────────────────────────

private fun TimelineEntry.toCacheEntity(adapter: com.squareup.moshi.JsonAdapter<Map<String, Any?>>): CachedTimelineEntity =
    CachedTimelineEntity(
        id           = id,
        kind         = kind,
        title        = title,
        description  = description,
        displayTime  = displayTime,
        timestamp    = timestamp,
        metadataJson = adapter.toJson(metadata)
    )

private fun CachedTimelineEntity.toTimelineEntry(adapter: com.squareup.moshi.JsonAdapter<Map<String, Any?>>): TimelineEntry =
    TimelineEntry(
        id          = id,
        kind        = kind,
        title       = title,
        description = description,
        iconEmoji   = null,
        displayTime = displayTime,
        timestamp   = timestamp,
        metadata    = adapter.fromJson(metadataJson) ?: emptyMap()
    )
