package com.cognicompanion.patient.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cognicompanion.patient.data.model.*
import com.cognicompanion.patient.data.remote.TokenStore
import com.cognicompanion.patient.data.repository.PatientRepository
import com.cognicompanion.patient.data.repository.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject

data class HomeUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val patientName: String = "",
    val dashboard: DashboardSummaryResponse? = null,
    val timeline: List<TimelineEntry> = emptyList(),
    val lastRefreshed: Long = 0L
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: PatientRepository,
    private val tokenStore: TokenStore
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        load()
        startPolling()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val name = tokenStore.getUserName() ?: "Patient"
            _uiState.value = _uiState.value.copy(patientName = name)

            val dashResult = repository.getDashboardSummary()
            val today = LocalDate.now().format(DateTimeFormatter.ISO_DATE)
            val timelineResult = repository.getTimeline(today)

            val dashboard = (dashResult as? Result.Success)?.data
            val timeline = (timelineResult as? Result.Success)?.data ?: emptyList()
            val error = (dashResult as? Result.Error)?.message

            _uiState.value = _uiState.value.copy(
                isLoading = false,
                dashboard = dashboard,
                timeline = timeline,
                error = error,
                lastRefreshed = System.currentTimeMillis()
            )
        }
    }

    fun logMedication(medicationId: String, taken: Boolean) {
        viewModelScope.launch {
            val today = LocalDate.now().format(DateTimeFormatter.ISO_DATE)
            repository.logMedication(medicationId, taken, today)
            // Refresh dashboard after logging
            delay(500)
            load()
        }
    }

    private fun startPolling() {
        viewModelScope.launch {
            while (isActive) {
                delay(60_000L) // Refresh every 60 seconds
                val today = LocalDate.now().format(DateTimeFormatter.ISO_DATE)
                val dashResult = repository.getDashboardSummary()
                val timelineResult = repository.getTimeline(today)
                val dashboard = (dashResult as? Result.Success)?.data
                val timeline = (timelineResult as? Result.Success)?.data ?: emptyList()
                if (dashboard != null) {
                    _uiState.value = _uiState.value.copy(
                        dashboard = dashboard,
                        timeline = timeline,
                        lastRefreshed = System.currentTimeMillis()
                    )
                }
            }
        }
    }
}
