package com.cognicompanion.patient.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.model.PatientResponse
import com.cognicompanion.patient.data.model.SupportedLanguage
import com.cognicompanion.patient.data.remote.TokenStore
import com.cognicompanion.patient.data.repository.AuthRepository
import com.cognicompanion.patient.data.repository.PatientRepository
import com.cognicompanion.patient.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val isLoading: Boolean = false,
    val profile: PatientResponse? = null,
    val error: String? = null,
    val selectedLanguage: SupportedLanguage = SupportedLanguage.ENGLISH,
    val simpleMode: Boolean = false,
    val textScale: Float = 1.0f,
    val highContrast: Boolean = false,
    val continuousVoice: Boolean = false,
    val loggedOut: Boolean = false
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val patientRepository: PatientRepository,
    private val authRepository: AuthRepository,
    private val tokenStore: TokenStore
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    init {
        load()
        viewModelScope.launch {
            tokenStore.languageCodeFlow.collect { code ->
                _uiState.value = _uiState.value.copy(
                    selectedLanguage = SupportedLanguage.fromCode(code)
                )
            }
        }
        viewModelScope.launch {
            tokenStore.simpleModeFlow.collect { enabled ->
                _uiState.value = _uiState.value.copy(simpleMode = enabled)
            }
        }
        viewModelScope.launch {
            tokenStore.textScaleFlow.collect { scale ->
                _uiState.value = _uiState.value.copy(textScale = scale)
            }
        }
        viewModelScope.launch {
            tokenStore.highContrastFlow.collect { enabled ->
                _uiState.value = _uiState.value.copy(highContrast = enabled)
            }
        }
        viewModelScope.launch {
            tokenStore.continuousVoiceFlow.collect { enabled ->
                _uiState.value = _uiState.value.copy(continuousVoice = enabled)
            }
        }
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = patientRepository.getMyProfile()) {
                is Result.Success -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    profile   = result.data
                )
                is Result.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error     = result.message
                )
            }
        }
    }

    fun selectLanguage(language: SupportedLanguage) {
        viewModelScope.launch {
            tokenStore.saveLanguageCode(language.bcp47Code)
        }
    }

    fun setSimpleMode(enabled: Boolean) {
        viewModelScope.launch {
            tokenStore.saveSimpleMode(enabled)
        }
    }

    fun setTextScale(scale: Float) {
        viewModelScope.launch {
            tokenStore.saveTextScale(scale)
        }
    }

    fun setHighContrast(enabled: Boolean) {
        viewModelScope.launch {
            tokenStore.saveHighContrast(enabled)
        }
    }

    fun setContinuousVoice(enabled: Boolean) {
        viewModelScope.launch {
            tokenStore.saveContinuousVoice(enabled)
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _uiState.value = _uiState.value.copy(loggedOut = true)
        }
    }
}
