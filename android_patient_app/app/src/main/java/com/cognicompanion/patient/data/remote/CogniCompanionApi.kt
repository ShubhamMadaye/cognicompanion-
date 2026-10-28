package com.cognicompanion.patient.data.remote

import com.cognicompanion.patient.data.model.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.*

interface CogniCompanionApi {

    // ── Auth ──────────────────────────────────────────────────────────────────

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @POST("auth/refresh")
    suspend fun refreshToken(@Body request: RefreshRequest): AccessTokenResponse

    @GET("auth/me")
    suspend fun getMe(): UserResponse

    @POST("auth/logout")
    suspend fun logout(): Any

    // ── Patients ──────────────────────────────────────────────────────────────

    @GET("patients/me")
    suspend fun getMyPatientProfile(): PatientResponse

    @GET("patients/{patientId}/dashboard-summary")
    suspend fun getDashboardSummary(
        @Path("patientId") patientId: String
    ): DashboardSummaryResponse

    // ── Timeline ──────────────────────────────────────────────────────────────

    @GET("patients/{patientId}/timeline")
    suspend fun getTimeline(
        @Path("patientId") patientId: String,
        @Query("day") day: String? = null
    ): List<TimelineEntry>

    // ── Memories ──────────────────────────────────────────────────────────────

    @GET("patients/{patientId}/memories")
    suspend fun getMemories(
        @Path("patientId") patientId: String,
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0
    ): List<MemoryListItem>

    @GET("patients/{patientId}/people")
    suspend fun getPeople(
        @Path("patientId") patientId: String
    ): List<PersonResponse>

    // ── Medication Log ────────────────────────────────────────────────────────

    @POST("patients/{patientId}/medications/{medicationId}/log")
    suspend fun logMedication(
        @Path("patientId") patientId: String,
        @Path("medicationId") medicationId: String,
        @Body request: LogMedicationRequest
    ): Any

    // ── Voice / Assistant ─────────────────────────────────────────────────────

    @POST("patients/{patientId}/conversations/message")
    suspend fun askAssistant(
        @Path("patientId") patientId: String,
        @Body request: AskAssistantRequest
    ): AskAssistantResponse

    @Multipart
    @POST("patients/{patientId}/voice/converse")
    suspend fun voiceConverse(
        @Path("patientId") patientId: String,
        @Part audio: MultipartBody.Part,
        @Part("language_code") languageCode: RequestBody,
        @Part("conversation_id") conversationId: RequestBody? = null
    ): VoiceConverseResponse

    @GET("patients/{patientId}/conversations")
    suspend fun listConversations(
        @Path("patientId") patientId: String,
        @Query("limit") limit: Int = 10
    ): List<ConversationResponse>

    // ── Games ─────────────────────────────────────────────────────────────────

    @GET("games")
    suspend fun listGames(): List<GameResponse>

    @POST("patients/{patientId}/games/{gameType}/generate")
    suspend fun generateGameContent(
        @Path("patientId") patientId: String,
        @Path("gameType") gameType: String,
        @Query("difficulty") difficulty: String = "MEDIUM",
        @Query("personalize") personalize: Boolean = true
    ): GameContentResponse

    @POST("patients/{patientId}/games/sessions")
    suspend fun recordGameSession(
        @Path("patientId") patientId: String,
        @Body request: CreateGameSessionRequest
    ): GameSessionResponse

    @GET("patients/{patientId}/games/sessions")
    suspend fun listGameSessions(
        @Path("patientId") patientId: String,
        @Query("limit") limit: Int = 20
    ): List<GameSessionResponse>
}
