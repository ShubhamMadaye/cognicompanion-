package com.cognicompanion.patient.ui.memories

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.model.MemoryListItem
import com.cognicompanion.patient.data.model.PersonResponse
import com.cognicompanion.patient.data.repository.PatientRepository
import com.cognicompanion.patient.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MemoriesUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val memories: List<MemoryListItem> = emptyList(),
    val people: List<PersonResponse> = emptyList(),
    val selectedTab: Int = 0  // 0 = Memories, 1 = People
)

@HiltViewModel
class MemoriesViewModel @Inject constructor(
    private val repository: PatientRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(MemoriesUiState())
    val uiState: StateFlow<MemoriesUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val memoriesResult = repository.getMemories()
            val peopleResult = repository.getPeople()

            val memories = (memoriesResult as? Result.Success)?.data ?: emptyList()
            val people = (peopleResult as? Result.Success)?.data ?: emptyList()
            val error = (memoriesResult as? Result.Error)?.message

            _uiState.value = _uiState.value.copy(
                isLoading = false,
                memories = memories,
                people = people,
                error = error
            )
        }
    }

    fun selectTab(index: Int) {
        _uiState.value = _uiState.value.copy(selectedTab = index)
    }
}
