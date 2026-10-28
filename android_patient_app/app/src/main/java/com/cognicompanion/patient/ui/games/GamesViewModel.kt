package com.cognicompanion.patient.ui.games

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.model.*
import com.cognicompanion.patient.data.repository.GamesRepository
import com.cognicompanion.patient.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class GameScreen {
    object Catalogue : GameScreen()
    data class Playing(val content: GameContentResponse, val game: GameResponse) : GameScreen()
    data class Result(val session: GameSessionResponse) : GameScreen()
}

data class GamesUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val games: List<GameResponse> = emptyList(),
    val screen: GameScreen = GameScreen.Catalogue,
    val isSubmitting: Boolean = false
)

@HiltViewModel
class GamesViewModel @Inject constructor(
    private val gamesRepository: GamesRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(GamesUiState())
    val uiState: StateFlow<GamesUiState> = _uiState.asStateFlow()

    init { loadCatalogue() }

    fun loadCatalogue() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null, screen = GameScreen.Catalogue)
            when (val result = gamesRepository.listGames()) {
                is Result.Success -> _uiState.value = _uiState.value.copy(
                    isLoading = false, games = result.data
                )
                is Result.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false, error = result.message
                )
            }
        }
    }

    fun startGame(game: GameResponse) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = gamesRepository.generateContent(game.gameType)) {
                is Result.Success -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    screen    = GameScreen.Playing(result.data, game)
                )
                is Result.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false, error = result.message
                )
            }
        }
    }

    fun submitSession(request: CreateGameSessionRequest) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSubmitting = true)
            when (val result = gamesRepository.submitSession(request)) {
                is Result.Success -> _uiState.value = _uiState.value.copy(
                    isSubmitting = false,
                    screen       = GameScreen.Result(result.data)
                )
                is Result.Error -> _uiState.value = _uiState.value.copy(
                    isSubmitting = false,
                    error        = result.message
                )
            }
        }
    }

    fun backToCatalogue() {
        _uiState.value = _uiState.value.copy(screen = GameScreen.Catalogue)
    }
}
