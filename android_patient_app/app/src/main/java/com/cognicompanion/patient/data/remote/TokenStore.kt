package com.cognicompanion.patient.data.remote

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.cognicompanion.patient.data.model.SupportedLanguage
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "cogni_session")

@Singleton
class TokenStore @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private val KEY_ACCESS_TOKEN   = stringPreferencesKey("access_token")
        private val KEY_REFRESH_TOKEN  = stringPreferencesKey("refresh_token")
        private val KEY_PATIENT_ID     = stringPreferencesKey("patient_id")
        private val KEY_USER_NAME      = stringPreferencesKey("user_name")
        private val KEY_USER_EMAIL     = stringPreferencesKey("user_email")
        private val KEY_BASE_URL       = stringPreferencesKey("base_url")
        private val KEY_LANGUAGE_CODE  = stringPreferencesKey("language_code")
        // Emergency contact cached from patient profile
        private val KEY_EMERGENCY_NAME  = stringPreferencesKey("emergency_name")
        private val KEY_EMERGENCY_PHONE = stringPreferencesKey("emergency_phone")
        private val KEY_DATE_OF_BIRTH   = stringPreferencesKey("date_of_birth")

        // Accessibility & continuous voice
        private val KEY_SIMPLE_MODE      = androidx.datastore.preferences.core.booleanPreferencesKey("simple_mode")
        private val KEY_TEXT_SCALE       = androidx.datastore.preferences.core.floatPreferencesKey("text_scale")
        private val KEY_HIGH_CONTRAST    = androidx.datastore.preferences.core.booleanPreferencesKey("high_contrast")
        private val KEY_CONTINUOUS_VOICE = androidx.datastore.preferences.core.booleanPreferencesKey("continuous_voice")
    }

    // ── Flows ─────────────────────────────────────────────────────────────────

    val accessTokenFlow: Flow<String?>   = context.dataStore.data.map { it[KEY_ACCESS_TOKEN] }
    val patientIdFlow: Flow<String?>     = context.dataStore.data.map { it[KEY_PATIENT_ID] }
    val baseUrlFlow: Flow<String?>       = context.dataStore.data.map { it[KEY_BASE_URL] }
    val languageCodeFlow: Flow<String>   = context.dataStore.data.map {
        it[KEY_LANGUAGE_CODE] ?: SupportedLanguage.ENGLISH.bcp47Code
    }
    val simpleModeFlow: Flow<Boolean>      = context.dataStore.data.map { it[KEY_SIMPLE_MODE] ?: false }
    val textScaleFlow: Flow<Float>         = context.dataStore.data.map { it[KEY_TEXT_SCALE] ?: 1.0f }
    val highContrastFlow: Flow<Boolean>    = context.dataStore.data.map { it[KEY_HIGH_CONTRAST] ?: false }
    val continuousVoiceFlow: Flow<Boolean> = context.dataStore.data.map { it[KEY_CONTINUOUS_VOICE] ?: false }

    fun isLoggedIn(): Flow<Boolean>      = accessTokenFlow.map { it != null }

    // ── Getters ───────────────────────────────────────────────────────────────

    suspend fun getAccessToken(): String?  = accessTokenFlow.first()
    suspend fun getRefreshToken(): String? = context.dataStore.data.first()[KEY_REFRESH_TOKEN]
    suspend fun getPatientId(): String?    = patientIdFlow.first()
    suspend fun getUserName(): String?     = context.dataStore.data.first()[KEY_USER_NAME]
    suspend fun getUserEmail(): String?    = context.dataStore.data.first()[KEY_USER_EMAIL]
    suspend fun getBaseUrl(): String?      = baseUrlFlow.first()
    suspend fun getLanguageCode(): String  = languageCodeFlow.first()
    suspend fun isSimpleMode(): Boolean    = simpleModeFlow.first()
    suspend fun getTextScale(): Float      = textScaleFlow.first()
    suspend fun isHighContrast(): Boolean  = highContrastFlow.first()
    suspend fun isContinuousVoice(): Boolean = continuousVoiceFlow.first()

    suspend fun getEmergencyName(): String?  = context.dataStore.data.first()[KEY_EMERGENCY_NAME]
    suspend fun getEmergencyPhone(): String? = context.dataStore.data.first()[KEY_EMERGENCY_PHONE]
    suspend fun getDateOfBirth(): String?    = context.dataStore.data.first()[KEY_DATE_OF_BIRTH]

    // ── Writers ───────────────────────────────────────────────────────────────

    suspend fun saveSession(
        accessToken: String,
        refreshToken: String,
        patientId: String,
        userName: String,
        userEmail: String
    ) {
        context.dataStore.edit { prefs ->
            prefs[KEY_ACCESS_TOKEN]  = accessToken
            prefs[KEY_REFRESH_TOKEN] = refreshToken
            prefs[KEY_PATIENT_ID]    = patientId
            prefs[KEY_USER_NAME]     = userName
            prefs[KEY_USER_EMAIL]    = userEmail
        }
    }

    suspend fun saveNewAccessToken(accessToken: String) {
        context.dataStore.edit { it[KEY_ACCESS_TOKEN] = accessToken }
    }

    suspend fun saveBaseUrl(url: String) {
        context.dataStore.edit { it[KEY_BASE_URL] = url }
    }

    /** Persists the BCP-47 language code the patient chose in Profile. */
    suspend fun saveLanguageCode(bcp47Code: String) {
        context.dataStore.edit { it[KEY_LANGUAGE_CODE] = bcp47Code }
    }

    /** Cache patient profile data locally so Profile screen loads offline. */
    suspend fun saveProfileCache(
        emergencyName: String?,
        emergencyPhone: String?,
        dateOfBirth: String?
    ) {
        context.dataStore.edit { prefs ->
            if (emergencyName != null) prefs[KEY_EMERGENCY_NAME] = emergencyName
            if (emergencyPhone != null) prefs[KEY_EMERGENCY_PHONE] = emergencyPhone
            if (dateOfBirth != null) prefs[KEY_DATE_OF_BIRTH] = dateOfBirth
        }
    }

    suspend fun saveSimpleMode(enabled: Boolean) {
        context.dataStore.edit { it[KEY_SIMPLE_MODE] = enabled }
    }

    suspend fun saveTextScale(scale: Float) {
        context.dataStore.edit { it[KEY_TEXT_SCALE] = scale }
    }

    suspend fun saveHighContrast(enabled: Boolean) {
        context.dataStore.edit { it[KEY_HIGH_CONTRAST] = enabled }
    }

    suspend fun saveContinuousVoice(enabled: Boolean) {
        context.dataStore.edit { it[KEY_CONTINUOUS_VOICE] = enabled }
    }

    suspend fun clearSession() {
        context.dataStore.edit { it.clear() }
    }
}
