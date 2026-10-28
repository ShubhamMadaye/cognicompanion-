package com.cognicompanion.patient.ui.today

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.cognicompanion.patient.data.model.TimelineEntry
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(
    viewModel: TodayViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    val dateLabel = remember {
        LocalDate.now().format(DateTimeFormatter.ofPattern("EEEE, d MMMM", Locale.ENGLISH))
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Today's Plan", fontWeight = FontWeight.SemiBold)
                        Text(
                            dateLabel,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                actions = {
                    if (uiState.pendingLogCount > 0) {
                        Badge(
                            containerColor = MaterialTheme.colorScheme.error
                        ) { Text("${uiState.pendingLogCount} pending") }
                        Spacer(Modifier.width(12.dp))
                    }
                }
            )
        }
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = uiState.isLoading,
            onRefresh = viewModel::load,
            modifier = Modifier.fillMaxSize().padding(padding)
        ) {
            when {
                uiState.error != null && uiState.entries.isEmpty() -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                            modifier = Modifier.padding(32.dp)
                        ) {
                            Icon(
                                if (uiState.isOffline) Icons.Default.WifiOff else Icons.Default.ErrorOutline,
                                contentDescription = null,
                                modifier = Modifier.size(40.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                uiState.error ?: "Error",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                style = MaterialTheme.typography.bodyMedium
                            )
                            Button(onClick = viewModel::load) { Text("Retry") }
                        }
                    }
                }
                uiState.entries.isEmpty() && !uiState.isLoading -> {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            "Nothing scheduled for today.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                else -> {
                    val grouped = uiState.entries.groupBy { entry ->
                        timeOfDayLabel(entry.displayTime)
                    }
                    LazyColumn(
                        contentPadding = PaddingValues(bottom = 24.dp)
                    ) {
                        grouped.forEach { (period, entries) ->
                            item(key = period) {
                                Text(
                                    period.uppercase(),
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(
                                        start = 20.dp, top = 20.dp, bottom = 6.dp
                                    )
                                )
                            }
                            items(entries, key = { it.id }) { entry ->
                                TimelineRow(
                                    entry = entry,
                                    onMarkTaken = { medicationId ->
                                        viewModel.markMedicationTaken(medicationId)
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TimelineRow(
    entry: TimelineEntry,
    onMarkTaken: (String) -> Unit
) {
    val taken = entry.metadata["taken"] as? Boolean ?: false
    val medicationId = entry.metadata["medication_id"] as? String

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 5.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Completion circle (only for medications)
        if (entry.kind == "medication" && medicationId != null) {
            IconButton(
                onClick = { if (!taken) onMarkTaken(medicationId) },
                modifier = Modifier.size(36.dp)
            ) {
                Icon(
                    if (taken) Icons.Default.CheckCircle else Icons.Default.RadioButtonUnchecked,
                    contentDescription = if (taken) "Taken" else "Mark taken",
                    tint = if (taken) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.outline
                )
            }
        } else {
            // Non-medication kind icon
            Surface(
                modifier = Modifier.size(36.dp),
                shape = MaterialTheme.shapes.small,
                color = MaterialTheme.colorScheme.surfaceVariant
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        kindIcon(entry.kind),
                        contentDescription = entry.kind,
                        modifier = Modifier.size(18.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Title + description
        Column(modifier = Modifier.weight(1f)) {
            Text(
                entry.title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
                textDecoration = if (taken) TextDecoration.LineThrough else TextDecoration.None,
                color = if (taken) MaterialTheme.colorScheme.onSurfaceVariant
                else MaterialTheme.colorScheme.onSurface
            )
            entry.description?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1
                )
            }
        }

        // Time badge
        Surface(
            shape = MaterialTheme.shapes.extraSmall,
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Text(
                entry.displayTime,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
            )
        }

        // "Take Dose" button for pending medications
        if (entry.kind == "medication" && !taken && medicationId != null) {
            Spacer(Modifier.width(4.dp))
            FilledTonalButton(
                onClick = { onMarkTaken(medicationId) },
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Text("Take Dose", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

private fun timeOfDayLabel(displayTime: String): String {
    return try {
        val upper = displayTime.uppercase()
        if (upper.contains("AM")) {
            val hour = displayTime.split(":")[0].trim().toIntOrNull() ?: 0
            if (hour < 12) "Morning" else "Afternoon"
        } else if (upper.contains("PM")) {
            val hour = displayTime.split(":")[0].trim().toIntOrNull() ?: 12
            if (hour == 12 || hour < 5) "Afternoon" else "Evening"
        } else {
            "Schedule"
        }
    } catch (_: Exception) {
        "Schedule"
    }
}

private fun kindIcon(kind: String): ImageVector = when (kind) {
    "medication" -> Icons.Default.Medication
    "routine"    -> Icons.Default.AccessTime
    "event"      -> Icons.Default.Event
    "memory"     -> Icons.Default.BookmarkBorder
    else         -> Icons.Default.Circle
}
