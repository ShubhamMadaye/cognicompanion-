package com.cognicompanion.patient.ui.games

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.cognicompanion.patient.data.model.*
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GamesScreen(
    viewModel: GamesViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    BackHandler(enabled = uiState.screen != GameScreen.Catalogue) {
        viewModel.backToCatalogue()
    }

    AnimatedContent(targetState = uiState.screen, label = "game_screen") { screen ->
        when (screen) {
            is GameScreen.Catalogue -> CatalogueView(uiState, viewModel)
            is GameScreen.Playing   -> PlayingView(screen.content, screen.game, viewModel)
            is GameScreen.Result    -> ResultView(screen.session, viewModel)
        }
    }
}

// ── Catalogue ─────────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CatalogueView(uiState: GamesUiState, viewModel: GamesViewModel) {
    Scaffold(
        topBar = { TopAppBar(title = { Text("Cognitive Games") }) }
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = uiState.isLoading,
            onRefresh    = viewModel::loadCatalogue,
            modifier     = Modifier.fillMaxSize().padding(padding)
        ) {
            when {
                uiState.error != null && uiState.games.isEmpty() -> ErrorState(uiState.error, viewModel::loadCatalogue)
                uiState.games.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No games available.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                else -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(uiState.games) { game ->
                        GameCard(game, onClick = { viewModel.startGame(game) }, isLoading = uiState.isLoading)
                    }
                }
            }
        }
    }
}

@Composable
private fun GameCard(game: GameResponse, onClick: () -> Unit, isLoading: Boolean) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick  = onClick
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(game.iconEmoji ?: "🧠", style = MaterialTheme.typography.headlineMedium)
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(game.name, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyLarge)
                game.description?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2)
                }
                Text(
                    "~${game.estimatedDurationSeconds / 60} min",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
            } else {
                Icon(Icons.Default.PlayArrow, contentDescription = "Play", tint = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

// ── Playing ───────────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PlayingView(content: GameContentResponse, game: GameResponse, viewModel: GamesViewModel) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(game.name) },
                navigationIcon = {
                    IconButton(onClick = viewModel::backToCatalogue) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            // Instructions
            Text(
                content.instructions,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(16.dp))

            when (content.gameType) {
                "WORD_RECALL", "OBJECT_RECOGNITION" -> WordRecallGame(content, game.gameType, viewModel)
                "FACE_NAME",  "MATCHING"            -> MatchingGame(content, game.gameType, viewModel)
                "SEQUENCE"                          -> SequenceGame(content, game.gameType, viewModel)
                else                                -> QuizGame(content, game.gameType, viewModel)
            }
        }
    }
}

// ── Word Recall / Object Recognition game ─────────────────────────────────────

@Composable
private fun WordRecallGame(content: GameContentResponse, gameType: String, viewModel: GamesViewModel) {
    val targets   = content.targetObjects ?: content.sequence ?: emptyList()
    val options   = content.candidateObjects ?: targets
    var phase     by remember { mutableStateOf(0) } // 0=study, 1=recall
    var selected  by remember { mutableStateOf(setOf<String>()) }
    var timeLeft  by remember { mutableIntStateOf(10) }
    var startTime by remember { mutableLongStateOf(System.currentTimeMillis()) }

    // Countdown during study phase
    LaunchedEffect(phase) {
        if (phase == 0) {
            timeLeft = 10
            while (timeLeft > 0) { delay(1000); timeLeft-- }
            phase = 1
        }
    }

    when (phase) {
        0 -> {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("Remember these items — $timeLeft s",
                    style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.height(200.dp)
                ) {
                    items(targets) { word ->
                        Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.primaryContainer) {
                            Text(word, modifier = Modifier.padding(10.dp),
                                textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onPrimaryContainer)
                        }
                    }
                }
            }
        }
        1 -> {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Which did you see?", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    items(options) { word ->
                        val isSelected = word in selected
                        Surface(
                            shape = MaterialTheme.shapes.medium,
                            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                            onClick = {
                                selected = if (isSelected) selected - word else selected + word
                            }
                        ) {
                            Text(word,
                                modifier = Modifier.padding(10.dp),
                                textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (isSelected) MaterialTheme.colorScheme.onPrimary
                                else MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
                Button(
                    onClick = {
                        val correct = selected.count { it in targets }
                        val elapsed = ((System.currentTimeMillis() - startTime) / 1000).toInt()
                        viewModel.submitSession(CreateGameSessionRequest(
                            gameType       = gameType,
                            score          = correct * 10,
                            accuracy       = if (targets.isNotEmpty()) correct.toDouble() / targets.size else 1.0,
                            correctItems   = correct,
                            totalItems     = targets.size,
                            mistakes       = (selected - targets.toSet()).size,
                            durationSeconds = elapsed
                        ))
                    },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Submit") }
            }
        }
    }
}

// ── Matching game ──────────────────────────────────────────────────────────────

@Composable
private fun MatchingGame(content: GameContentResponse, gameType: String, viewModel: GamesViewModel) {
    val cards      = remember { (content.cards ?: emptyList()).shuffled() }
    var flipped    by remember { mutableStateOf(setOf<String>()) }
    var matched    by remember { mutableStateOf(setOf<String>()) }
    var lastCard   by remember { mutableStateOf<GameCardItem?>(null) }
    var mistakes   by remember { mutableIntStateOf(0) }
    val startTime  = remember { System.currentTimeMillis() }

    val isDone = matched.size == cards.size

    LaunchedEffect(isDone) {
        if (isDone) {
            delay(500)
            val elapsed = ((System.currentTimeMillis() - startTime) / 1000).toInt()
            viewModel.submitSession(CreateGameSessionRequest(
                gameType        = gameType,
                score           = maxOf(0, 100 - mistakes * 5),
                accuracy        = if (cards.isNotEmpty()) matched.size.toDouble() / cards.size else 1.0,
                correctItems    = matched.size / 2,
                totalItems      = cards.size / 2,
                mistakes        = mistakes,
                durationSeconds = elapsed
            ))
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Match the pairs", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        LazyVerticalGrid(
            columns = GridCells.Fixed(4),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.weight(1f)
        ) {
            items(cards) { card ->
                val isFlipped  = card.id in flipped || card.id in matched
                val isMatched  = card.id in matched
                OutlinedCard(
                    onClick = {
                        if (isFlipped || isDone) return@OutlinedCard
                        val current = lastCard
                        flipped = flipped + card.id
                        if (current == null) {
                            lastCard = card
                        } else {
                            if (current.pairId == card.pairId) {
                                matched = matched + current.id + card.id
                            } else {
                                mistakes++
                            }
                            lastCard = null
                        }
                    },
                    border = if (isMatched) BorderStroke(2.dp, MaterialTheme.colorScheme.primary) else BorderStroke(0.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0f)),
                    colors = CardDefaults.outlinedCardColors(
                        containerColor = when {
                            isMatched -> MaterialTheme.colorScheme.primaryContainer
                            isFlipped -> MaterialTheme.colorScheme.surfaceVariant
                            else      -> MaterialTheme.colorScheme.surface
                        }
                    )
                ) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier.fillMaxWidth().height(60.dp)
                    ) {
                        if (isFlipped) {
                            Text(card.emoji ?: card.label,
                                style = MaterialTheme.typography.bodyMedium,
                                textAlign = TextAlign.Center,
                                fontWeight = FontWeight.SemiBold)
                        } else {
                            Text("?", style = MaterialTheme.typography.titleLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
        Text(
            "Mistakes: $mistakes",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

// ── Sequence game ─────────────────────────────────────────────────────────────

@Composable
private fun SequenceGame(content: GameContentResponse, gameType: String, viewModel: GamesViewModel) {
    val sequence  = content.sequence ?: emptyList()
    var phase     by remember { mutableStateOf(0) }  // 0=study, 1=recall
    var userSeq   by remember { mutableStateOf(listOf<String>()) }
    var timeLeft  by remember { mutableIntStateOf(8) }
    val startTime = remember { System.currentTimeMillis() }

    LaunchedEffect(phase) {
        if (phase == 0) {
            timeLeft = 8
            while (timeLeft > 0) { delay(1000); timeLeft-- }
            phase = 1
        }
    }

    when (phase) {
        0 -> Column(verticalArrangement = Arrangement.spacedBy(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Remember the sequence — $timeLeft s", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                sequence.forEachIndexed { i, item ->
                    Surface(shape = MaterialTheme.shapes.small, color = MaterialTheme.colorScheme.primaryContainer) {
                        Text("${i + 1}. $item",
                            modifier = Modifier.padding(10.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer)
                    }
                }
            }
        }
        1 -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Recreate the sequence (${userSeq.size}/${sequence.size})",
                style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            // Shown selected order
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                userSeq.forEachIndexed { i, s ->
                    AssistChip(onClick = {}, label = { Text("${i + 1}. $s") })
                }
            }
            // Shuffled buttons
            val shuffled = remember { sequence.shuffled() }
            LazyVerticalGrid(
                columns = GridCells.Fixed(3),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.weight(1f)
            ) {
                items(shuffled) { item ->
                    OutlinedButton(
                        onClick = { if (userSeq.size < sequence.size) userSeq = userSeq + item },
                        enabled = item !in userSeq
                    ) { Text(item, style = MaterialTheme.typography.bodySmall) }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { userSeq = emptyList() }, modifier = Modifier.weight(1f)) { Text("Reset") }
                Button(
                    onClick = {
                        val correct = userSeq.zip(sequence).count { (a, b) -> a == b }
                        val elapsed = ((System.currentTimeMillis() - startTime) / 1000).toInt()
                        viewModel.submitSession(CreateGameSessionRequest(
                            gameType        = gameType,
                            score           = correct * 10,
                            accuracy        = if (sequence.isNotEmpty()) correct.toDouble() / sequence.size else 1.0,
                            correctItems    = correct,
                            totalItems      = sequence.size,
                            mistakes        = sequence.size - correct,
                            durationSeconds = elapsed
                        ))
                    },
                    enabled = userSeq.size == sequence.size,
                    modifier = Modifier.weight(1f)
                ) { Text("Submit") }
            }
        }
    }
}

// ── Quiz / Q&A game ────────────────────────────────────────────────────────────

@Composable
private fun QuizGame(content: GameContentResponse, gameType: String, viewModel: GamesViewModel) {
    val questions = content.questions ?: emptyList()
    var index     by remember { mutableIntStateOf(0) }
    var selected  by remember { mutableStateOf<String?>(null) }
    var correct   by remember { mutableIntStateOf(0) }
    var mistakes  by remember { mutableIntStateOf(0) }
    val startTime = remember { System.currentTimeMillis() }

    if (questions.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("No questions available.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    val q = questions[index]

    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        LinearProgressIndicator(
            progress = { (index + 1).toFloat() / questions.size },
            modifier = Modifier.fillMaxWidth()
        )
        Text(
            "Question ${index + 1} of ${questions.size}",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(q.questionText, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

        q.options.forEach { option ->
            val isSelected   = selected == option
            val isCorrect    = selected != null && option == q.correctOption
            val isWrong      = isSelected && option != q.correctOption
            OutlinedButton(
                onClick  = { if (selected == null) selected = option },
                modifier = Modifier.fillMaxWidth(),
                colors   = ButtonDefaults.outlinedButtonColors(
                    containerColor = when {
                        isCorrect -> MaterialTheme.colorScheme.primaryContainer
                        isWrong   -> MaterialTheme.colorScheme.errorContainer
                        else      -> MaterialTheme.colorScheme.surface
                    }
                )
            ) {
                Text(option, textAlign = TextAlign.Start, modifier = Modifier.fillMaxWidth())
            }
        }

        if (selected != null) {
            val last = index == questions.size - 1
            Button(
                onClick = {
                    if (selected == q.correctOption) correct++ else mistakes++
                    if (last) {
                        val elapsed = ((System.currentTimeMillis() - startTime) / 1000).toInt()
                        viewModel.submitSession(CreateGameSessionRequest(
                            gameType        = gameType,
                            score           = correct * (100 / questions.size),
                            accuracy        = correct.toDouble() / questions.size,
                            correctItems    = correct,
                            totalItems      = questions.size,
                            mistakes        = mistakes,
                            durationSeconds = elapsed
                        ))
                    } else {
                        selected = null
                        index++
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (last) "Submit" else "Next")
            }
        }
    }
}

// ── Result ────────────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ResultView(session: GameSessionResponse, viewModel: GamesViewModel) {
    Scaffold(
        topBar = { TopAppBar(title = { Text("Game Complete") }) }
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically)
        ) {
            Icon(Icons.Default.CheckCircle, null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.primary)

            Text("Well done!", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    ResultRow("Score", "${session.score ?: 0}")
                    ResultRow("Accuracy", "${((session.accuracy ?: 0.0) * 100).toInt()}%")
                    session.mistakes?.let { ResultRow("Mistakes", "$it") }
                    session.correctItems?.let { ResultRow("Correct", "$it / ${session.totalItems}") }
                    session.durationSeconds?.let { ResultRow("Time", "${it}s") }
                    session.nextDifficulty?.let {
                        ResultRow("Next difficulty", it.lowercase().replaceFirstChar { c -> c.uppercase() })
                    }
                }
            }

            Button(onClick = viewModel::backToCatalogue, modifier = Modifier.fillMaxWidth()) {
                Text("Back to Games")
            }
        }
    }
}

@Composable
private fun ResultRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
        Text(value, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ErrorState(error: String, onRetry: () -> Unit) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.padding(32.dp)
        ) {
            Icon(Icons.Default.ErrorOutline, null,
                modifier = Modifier.size(40.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(error, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
            Button(onClick = onRetry) { Text("Retry") }
        }
    }
}
