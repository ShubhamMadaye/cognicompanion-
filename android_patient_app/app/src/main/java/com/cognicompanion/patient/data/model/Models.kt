package com.cognicompanion.patient.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

// ─────────────────────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class LoginRequest(
    val email: String,
    val password: String
)

@JsonClass(generateAdapter = true)
data class RefreshRequest(
    @Json(name = "refresh_token") val refreshToken: String
)

@JsonClass(generateAdapter = true)
data class AccessTokenResponse(
    @Json(name = "access_token") val accessToken: String
)

@JsonClass(generateAdapter = true)
data class TokenResponse(
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "refresh_token") val refreshToken: String,
    val user: UserResponse
)

@JsonClass(generateAdapter = true)
data class UserResponse(
    val id: String,
    val email: String,
    @Json(name = "full_name") val fullName: String,
    val role: String,
    @Json(name = "is_active") val isActive: Boolean,
    @Json(name = "created_at") val createdAt: String
)

// ─────────────────────────────────────────────────────────────────────────────
// Patient
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class PatientResponse(
    val id: String,
    @Json(name = "user_id") val userId: String,
    @Json(name = "date_of_birth") val dateOfBirth: String?,
    @Json(name = "preferred_language") val preferredLanguage: String,
    @Json(name = "profile_photo_url") val profilePhotoUrl: String?,
    @Json(name = "emergency_contact_name") val emergencyContactName: String?,
    @Json(name = "emergency_contact_phone") val emergencyContactPhone: String?,
    @Json(name = "created_at") val createdAt: String,
    val user: UserResponse
)

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class DashboardSummaryResponse(
    val patient: PatientResponse,
    val today: TodaySummary,
    val cognitive: CognitiveSummary,
    val memory: MemorySummary,
    val attention: AttentionSummary
)

@JsonClass(generateAdapter = true)
data class TodaySummary(
    @Json(name = "total_medications") val totalMedications: Int = 0,
    @Json(name = "taken_medications") val takenMedications: Int = 0,
    @Json(name = "pending_medications") val pendingMedications: Int = 0,
    @Json(name = "total_routines") val totalRoutines: Int = 0,
    @Json(name = "completed_routines") val completedRoutines: Int = 0,
    @Json(name = "total_events") val totalEvents: Int = 0
)

@JsonClass(generateAdapter = true)
data class CognitiveSummary(
    val status: String,
    @Json(name = "cpi_score") val cpiScore: Double?,
    @Json(name = "cpi_delta") val cpiDelta: Double?,
    @Json(name = "games_completed_today") val gamesCompletedToday: Int = 0,
    val disclaimer: String
)

@JsonClass(generateAdapter = true)
data class MemorySummary(
    @Json(name = "total_memories") val totalMemories: Int = 0,
    @Json(name = "total_people") val totalPeople: Int = 0,
    @Json(name = "latest_memory_title") val latestMemoryTitle: String?,
    @Json(name = "latest_memory_date") val latestMemoryDate: String?
)

@JsonClass(generateAdapter = true)
data class AttentionSummary(
    @Json(name = "pending_medication_names") val pendingMedicationNames: List<String> = emptyList(),
    @Json(name = "missed_medications") val missedMedications: Int = 0,
    val alerts: List<String> = emptyList()
)

// ─────────────────────────────────────────────────────────────────────────────
// Timeline
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class TimelineEntry(
    val kind: String,       // "routine" | "medication" | "event" | "memory"
    val id: String,
    val title: String,
    val description: String?,
    @Json(name = "icon_emoji") val iconEmoji: String?,
    val timestamp: String,
    @Json(name = "display_time") val displayTime: String,
    val metadata: Map<String, Any?> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class LogMedicationRequest(
    @Json(name = "log_date") val logDate: String,
    val taken: Boolean
)

// ─────────────────────────────────────────────────────────────────────────────
// Memories
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class MemoryListItem(
    val id: String,
    @Json(name = "patient_id") val patientId: String,
    @Json(name = "memory_type") val memoryType: String,
    val title: String,
    @Json(name = "event_date") val eventDate: String,
    @Json(name = "is_significant") val isSignificant: Boolean,
    val location: String?,
    @Json(name = "media_count") val mediaCount: Int = 0,
    @Json(name = "created_at") val createdAt: String
)

@JsonClass(generateAdapter = true)
data class PersonResponse(
    val id: String,
    @Json(name = "patient_id") val patientId: String,
    val name: String,
    val relationship: String?,
    val description: String?,
    @Json(name = "photo_url") val photoUrl: String?,
    @Json(name = "is_active") val isActive: Boolean,
    @Json(name = "created_at") val createdAt: String
)

// ─────────────────────────────────────────────────────────────────────────────
// Voice / Assistant
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class AskAssistantRequest(
    val query: String,
    @Json(name = "conversation_id") val conversationId: String? = null,
    @Json(name = "language_code") val languageCode: String = "en-IN",
    @Json(name = "image_base64") val imageBase64: String? = null
)

@JsonClass(generateAdapter = true)
data class ConfidenceInfo(
    val score: Double,
    val level: String
)

@JsonClass(generateAdapter = true)
data class GroundedSource(
    @Json(name = "source_type") val sourceType: String,
    val id: String,
    val title: String,
    val summary: String?,
    val date: String?
)

@JsonClass(generateAdapter = true)
data class AskAssistantResponse(
    @Json(name = "conversation_id") val conversationId: String,
    val answer: String,
    val reply: String,
    val intent: String,
    val confidence: Double,
    @Json(name = "confidence_info") val confidenceInfo: ConfidenceInfo,
    val sources: List<GroundedSource> = emptyList(),
    val grounded: Boolean = true,
    @Json(name = "audio_base64") val audioBase64: String?,
    @Json(name = "created_at") val createdAt: String
)

@JsonClass(generateAdapter = true)
data class VoiceConverseResponse(
    @Json(name = "conversation_id") val conversationId: String,
    val transcript: String,
    val answer: String,
    val reply: String,
    val intent: String,
    val confidence: Double,
    val sources: List<GroundedSource> = emptyList(),
    val grounded: Boolean = true,
    @Json(name = "audio_base64") val audioBase64: String?,
    @Json(name = "created_at") val createdAt: String
)

@JsonClass(generateAdapter = true)
data class ConversationMessage(
    val id: String,
    val role: String,   // "user" | "assistant"
    val content: String,
    @Json(name = "intent_type") val intentType: String?,
    @Json(name = "confidence_score") val confidenceScore: Double?,
    @Json(name = "created_at") val createdAt: String
)

@JsonClass(generateAdapter = true)
data class ConversationResponse(
    val id: String,
    @Json(name = "patient_id") val patientId: String,
    @Json(name = "started_at") val startedAt: String,
    @Json(name = "language_code") val languageCode: String?,
    @Json(name = "message_count") val messageCount: Int,
    val messages: List<ConversationMessage> = emptyList()
)

// ─────────────────────────────────────────────────────────────────────────────
// Games
// ─────────────────────────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class GameResponse(
    val id: String,
    @Json(name = "game_type") val gameType: String,
    val name: String,
    val description: String?,
    val instructions: String?,
    @Json(name = "min_difficulty") val minDifficulty: String,
    @Json(name = "max_difficulty") val maxDifficulty: String,
    @Json(name = "estimated_duration_seconds") val estimatedDurationSeconds: Int,
    @Json(name = "icon_emoji") val iconEmoji: String?
)

@JsonClass(generateAdapter = true)
data class GameCardItem(
    val id: String,
    @Json(name = "pair_id") val pairId: String,
    val label: String,
    val emoji: String?
)

@JsonClass(generateAdapter = true)
data class GameQuestionItem(
    @Json(name = "question_text") val questionText: String,
    val options: List<String>,
    @Json(name = "correct_option") val correctOption: String,
    @Json(name = "memory_id") val memoryId: String?
)

@JsonClass(generateAdapter = true)
data class GameContentResponse(
    @Json(name = "game_type") val gameType: String,
    @Json(name = "difficulty_level") val difficultyLevel: String,
    @Json(name = "is_personalized") val isPersonalized: Boolean,
    val instructions: String,
    val cards: List<GameCardItem>?,
    val sequence: List<String>?,
    val questions: List<GameQuestionItem>?,
    @Json(name = "target_objects") val targetObjects: List<String>?,
    @Json(name = "candidate_objects") val candidateObjects: List<String>?
)

@JsonClass(generateAdapter = true)
data class CreateGameSessionRequest(
    @Json(name = "game_type") val gameType: String,
    @Json(name = "difficulty_level") val difficultyLevel: String = "MEDIUM",
    val score: Int = 0,
    val accuracy: Double = 1.0,
    @Json(name = "reaction_time_ms") val reactionTimeMs: Int? = null,
    val mistakes: Int = 0,
    @Json(name = "total_items") val totalItems: Int = 1,
    @Json(name = "correct_items") val correctItems: Int = 1,
    @Json(name = "duration_seconds") val durationSeconds: Int? = null
)

@JsonClass(generateAdapter = true)
data class GameSessionResponse(
    val id: String,
    @Json(name = "patient_id") val patientId: String,
    @Json(name = "game_type") val gameType: String?,
    val status: String,
    @Json(name = "difficulty_level") val difficultyLevel: String,
    val score: Int?,
    val accuracy: Double?,
    val mistakes: Int?,
    @Json(name = "total_items") val totalItems: Int?,
    @Json(name = "correct_items") val correctItems: Int?,
    @Json(name = "next_difficulty") val nextDifficulty: String?,
    @Json(name = "duration_seconds") val durationSeconds: Int?,
    @Json(name = "started_at") val startedAt: String,
    @Json(name = "completed_at") val completedAt: String?
)

// ─────────────────────────────────────────────────────────────────────────────
// Language support
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Supported languages with their BCP-47 locale tags.
 * Only languages that have been verified through the full STT→PME→TTS pipeline.
 */
enum class SupportedLanguage(
    val displayName: String,
    val nativeName: String,
    val bcp47Code: String,
    val voiceSupported: Boolean
) {
    ENGLISH("English", "English", "en-IN", true),
    HINDI("Hindi", "हिंदी", "hi-IN", true),
    ASSAMESE("Assamese", "অসমীয়া", "as-IN", true),
    MEITEI("Meitei (Manipuri)", "মৈতৈলোন্", "mni-IN", true),
    KHASI("Khasi", "Ka Ktien Khasi", "kha-IN", false),   // TTS not available, text only
    GARO("Garo", "Abeng", "grt-IN", false),
    MIZO("Mizo", "Mizo ṭawng", "lus-IN", false),
    KOKBOROK("Kokborok", "ককবরক", "trp-IN", false),
    NAGA("Nagamese", "Nagamese", "nag-IN", false),
    NYISHI("Nyishi", "Nyishi", "njz-IN", false),
    PNAR("Pnar", "Pnar", "pbv-IN", false);

    companion object {
        fun fromCode(code: String): SupportedLanguage =
            entries.firstOrNull { it.bcp47Code == code } ?: ENGLISH
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Room cache entity — offline timeline
// ─────────────────────────────────────────────────────────────────────────────

@Entity(tableName = "cached_timeline")
data class CachedTimelineEntity(
    @PrimaryKey val id: String,
    val kind: String,
    val title: String,
    val description: String?,
    val displayTime: String,
    val timestamp: String,
    val metadataJson: String,   // JSON-encoded metadata map
    val cachedAt: Long = System.currentTimeMillis()
)

// Pending medication log to sync when back online
@Entity(tableName = "pending_medication_logs")
data class PendingMedicationLog(
    @PrimaryKey val localId: String,
    val medicationId: String,
    val logDate: String,
    val taken: Boolean,
    val createdAt: Long = System.currentTimeMillis()
)
