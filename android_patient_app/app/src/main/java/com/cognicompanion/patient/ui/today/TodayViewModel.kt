package com.cognicompanion.patient.ui.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.model.TimelineEntry
import com.cognicompanion.patient.data.repository.PatientRepository
import com.cognicompanion.patient.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject

data class TodayUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val isOffline: Boolean = false,
    val entries: List<TimelineEntry> = emptyList(),
    val pendingLogCount: Int = 0
)

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val repository: PatientRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(TodayUiState())
    val uiState: StateFlow<TodayUiState> = _uiState.asStateFlow()

    init {
        load()
        viewModelScope.launch {
            repository.pendingLogCount().collect { count ->
                _uiState.value = _uiState.value.copy(pendingLogCount = count)
            }
        }
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val today = LocalDate.now().format(DateTimeFormatter.ISO_DATE)
            when (val result = repository.getTimeline(today)) {
                is Result.Success -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    entries   = result.data,
                    isOffline = false
                )
                is Result.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error     = result.message,
                    isOffline = result.isOffline
                )
            }
        }
    }

    fun markMedicationTaken(medicationId: String) {
        viewModelScope.launch {
            val today = LocalDate.now().format(DateTimeFormatter.ISO_DATE)
            repository.logMedication(medicationId, true, today)
            load()
        }
    }
}
