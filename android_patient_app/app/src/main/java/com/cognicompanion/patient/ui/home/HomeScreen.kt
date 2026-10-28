package com.cognicompanion.patient.ui.home

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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.cognicompanion.patient.data.model.TimelineEntry
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onLogout: () -> Unit,
    onOpenToday: () -> Unit = {},
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            "Hello, ${uiState.patientName.split(" ").first()}",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        if (uiState.lastRefreshed > 0) {
                            val time = SimpleDateFormat("h:mm a", Locale.getDefault())
                                .format(Date(uiState.lastRefreshed))
                            Text(
                                "Updated $time",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Default.Logout, contentDescription = "Logout")
                    }
                }
            )
        }
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = uiState.isLoading,
            onRefresh = viewModel::load,
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (uiState.error != null && uiState.dashboard == null) {
                // Full-screen error state
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Icon(
                            Icons.Default.WifiOff,
                            contentDescription = null,
                            modifier = Modifier.size(48.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            uiState.error ?: "Could not connect",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Button(onClick = viewModel::load) { Text("Retry") }
                    }
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Dashboard summary cards
                    uiState.dashboard?.let { dash ->
                        item {
                            Text(
                                "Today's Overview",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        item { TodaySummaryCard(dash.today) }
                        item { CognitiveSummaryCard(dash.cognitive) }
                        if (dash.attention.pendingMedicationNames.isNotEmpty() ||
                            dash.attention.alerts.isNotEmpty()
                        ) {
                            item { AttentionCard(dash.attention) }
                        }
                    }

                    item {
                        OutlinedButton(onClick = onOpenToday, modifier = Modifier.fillMaxWidth()) {
                            Text("View full daily plan")
                        }
                    }

                    // Timeline section
                    if (uiState.timeline.isNotEmpty()) {
                        item {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                "Today's Schedule",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        items(uiState.timeline) { entry ->
                            TimelineEntryCard(entry, viewModel)
                        }
                    } else if (!uiState.isLoading && uiState.dashboard != null) {
                        item {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                "Today's Schedule",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        item {
                            Card(modifier = Modifier.fillMaxWidth()) {
                                Box(
                                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        "Nothing scheduled for today.",
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    }

                    item { Spacer(Modifier.height(16.dp)) }
                }
            }
        }
    }
}

@Composable
private fun TodaySummaryCard(today: com.cognicompanion.patient.data.model.TodaySummary) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Medications", style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                StatItem("Taken", today.takenMedications.toString())
                StatItem("Pending", today.pendingMedications.toString())
                StatItem("Total", today.totalMedications.toString())
            }
            if (today.totalRoutines > 0) {
                Divider()
                Text("Routines", style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                    StatItem("Done", today.completedRoutines.toString())
                    StatItem("Total", today.totalRoutines.toString())
                }
            }
        }
    }
}

@Composable
private fun CognitiveSummaryCard(cognitive: com.cognicompanion.patient.data.model.CognitiveSummary) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Cognitive Status", style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(cognitive.status, style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold)
                cognitive.cpiScore?.let { score ->
                    Column(horizontalAlignment = Alignment.End) {
                        Text("CPI: %.1f".format(score),
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Medium)
                        cognitive.cpiDelta?.let { delta ->
                            val sign = if (delta >= 0) "+" else ""
                            Text(
                                "$sign%.1f".format(delta),
                                style = MaterialTheme.typography.labelSmall,
                                color = if (delta >= 0) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }
            }
            if (cognitive.gamesCompletedToday > 0) {
                Text(
                    "${cognitive.gamesCompletedToday} game(s) completed today",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Text(
                cognitive.disclaimer,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun AttentionCard(attention: com.cognicompanion.patient.data.model.AttentionSummary) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        )
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                "Needs Attention",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onErrorContainer
            )
            attention.pendingMedicationNames.forEach { med ->
                Text(
                    "Pending: $med",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }
            attention.alerts.forEach { alert ->
                Text(
                    alert,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }
        }
    }
}

@Composable
private fun TimelineEntryCard(entry: TimelineEntry, viewModel: HomeViewModel) {
    val kindIcon = when (entry.kind) {
        "medication" -> Icons.Default.Medication
        "routine" -> Icons.Default.AccessTime
        "event" -> Icons.Default.Event
        "memory" -> Icons.Default.BookmarkBorder
        else -> Icons.Default.Circle
    }

    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Time badge
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.width(48.dp)
            ) {
                Text(
                    entry.displayTime,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(4.dp))
                Icon(
                    kindIcon,
                    contentDescription = entry.kind,
                    modifier = Modifier.size(18.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Content
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    entry.title,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                entry.description?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                // Show taken status for medication
                if (entry.kind == "medication") {
                    val taken = entry.metadata["taken"] as? Boolean
                    val medId = entry.metadata["medication_id"] as? String
                    if (medId != null) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.padding(top = 4.dp)
                        ) {
                            if (taken == true) {
                                AssistChip(
                                    onClick = {},
                                    label = { Text("Taken") },
                                    leadingIcon = {
                                        Icon(Icons.Default.Check, null, modifier = Modifier.size(14.dp))
                                    }
                                )
                            } else {
                                OutlinedButton(
                                    onClick = { viewModel.logMedication(medId, true) },
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
                                ) {
                                    Text("Mark taken", style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Text(label, style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
