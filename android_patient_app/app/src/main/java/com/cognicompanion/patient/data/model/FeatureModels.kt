package com.cognicompanion.patient.data.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class VoiceConverseRequest(
    val query: String,
    @Json(name = "language_code") val languageCode: String? = null,
    @Json(name = "conversation_id") val conversationId: String? = null
)

@JsonClass(generateAdapter = true)
data class GameSessionRequest(
    @Json(name = "game_id") val gameId: String,
    val score: Double,
    @Json(name = "duration_seconds") val durationSeconds: Int,
    @Json(name = "accuracy_percentage") val accuracyPercentage: Double,
    @Json(name = "difficulty_level") val difficultyLevel: String
)

@JsonClass(generateAdapter = true)
data class GameDefinition(
    val id: String,
    val name: String,
    val category: String? = null,
    val description: String? = null
)
