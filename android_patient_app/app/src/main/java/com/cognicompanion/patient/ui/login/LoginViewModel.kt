package com.cognicompanion.patient.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.remote.TokenStore
import com.cognicompanion.patient.data.repository.AuthRepository
import com.cognicompanion.patient.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val email: String = "",
    val password: String = "",
    val serverUrl: String = "",
    val isLoading: Boolean = false,
    val error: String? = null,
    val isLoggedIn: Boolean = false,
    val isOfflineError: Boolean = false
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val tokenStore: TokenStore
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val token = tokenStore.getAccessToken()
            val savedUrl = tokenStore.getBaseUrl() ?: "http://10.0.2.2:8000/api/v1/"
            _uiState.value = _uiState.value.copy(
                serverUrl = savedUrl,
                isLoggedIn = token != null
            )
        }
    }

    fun onEmailChange(value: String) {
        _uiState.value = _uiState.value.copy(email = value, error = null)
    }

    fun onPasswordChange(value: String) {
        _uiState.value = _uiState.value.copy(password = value, error = null)
    }

    fun onServerUrlChange(value: String) {
        _uiState.value = _uiState.value.copy(serverUrl = value)
    }

    fun login() {
        val state = _uiState.value
        if (state.email.isBlank()) {
            _uiState.value = state.copy(error = "Please enter your email address.")
            return
        }
        if (state.password.isBlank()) {
            _uiState.value = state.copy(error = "Please enter your password.")
            return
        }
        viewModelScope.launch {
            // Persist the server URL before login so Retrofit uses it on next start
            val url = state.serverUrl.trim().trimEnd('/') + "/"
            tokenStore.saveBaseUrl(url)
            _uiState.value = state.copy(isLoading = true, error = null, isOfflineError = false)
            when (val result = authRepository.login(state.email.trim(), state.password)) {
                is Result.Success -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isLoggedIn = true
                )
                is Result.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = result.message,
                    isOfflineError = result.isOffline
                )
            }
        }
    }
}
