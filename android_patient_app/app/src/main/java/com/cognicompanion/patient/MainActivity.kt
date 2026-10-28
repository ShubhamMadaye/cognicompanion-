package com.cognicompanion.patient

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.*
import com.cognicompanion.patient.data.remote.TokenStore
import com.cognicompanion.patient.data.repository.AuthRepository
import com.cognicompanion.patient.ui.games.GamesScreen
import com.cognicompanion.patient.ui.home.HomeScreen
import com.cognicompanion.patient.ui.login.LoginScreen
import com.cognicompanion.patient.ui.memories.MemoriesScreen
import com.cognicompanion.patient.ui.profile.ProfileScreen
import com.cognicompanion.patient.ui.theme.CogniCompanionTheme
import com.cognicompanion.patient.ui.today.TodayScreen
import com.cognicompanion.patient.ui.voice.VoiceAssistantScreen
import com.cognicompanion.patient.util.AppStrings
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var tokenStore: TokenStore
    @Inject lateinit var authRepository: AuthRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val textScale by tokenStore.textScaleFlow.collectAsStateWithLifecycle(initialValue = 1.0f)
            val simpleMode by tokenStore.simpleModeFlow.collectAsStateWithLifecycle(initialValue = false)
            val highContrast by tokenStore.highContrastFlow.collectAsStateWithLifecycle(initialValue = false)
            val effectiveScale = if (simpleMode) maxOf(textScale, 1.25f) else textScale

            CogniCompanionTheme(
                highContrast = highContrast,
                textScale = effectiveScale
            ) {
                CogniCompanionApp(tokenStore, authRepository)
            }
        }
    }
}

private data class NavItem(val route: String, val stringKey: String, val icon: ImageVector)

private val bottomNavItems = listOf(
    NavItem("home",     "nav_home",     Icons.Default.Home),
    NavItem("today",    "nav_today",    Icons.Default.DateRange),
    NavItem("voice",    "nav_voice",    Icons.Default.Mic),
    NavItem("games",    "nav_games",    Icons.Default.Psychology),
    NavItem("memories", "nav_memories", Icons.Default.BookmarkBorder),
    NavItem("profile",  "nav_profile",  Icons.Default.Person)
)

private val mainRoutes = bottomNavItems.map { it.route }.toSet()

@Composable
private fun CogniCompanionApp(tokenStore: TokenStore, authRepository: AuthRepository) {
    val navController = rememberNavController()
    val scope         = rememberCoroutineScope()
    val isLoggedIn    by tokenStore.isLoggedIn().collectAsStateWithLifecycle(initialValue = null)
    val languageCode  by tokenStore.languageCodeFlow.collectAsStateWithLifecycle(initialValue = "en-IN")

    val startDestination = when (isLoggedIn) {
        true  -> "home"
        false -> "login"
        null  -> return   // Still reading DataStore — show nothing
    }

    val currentBackStack by navController.currentBackStackEntryAsState()
    val currentRoute     = currentBackStack?.destination?.route
    val showBottomBar    = currentRoute in mainRoutes

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomNavItems.forEach { item ->
                        val label = AppStrings.get(item.stringKey, languageCode)
                        NavigationBarItem(
                            selected = currentRoute == item.route,
                            onClick  = {
                                navController.navigate(item.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState    = true
                                }
                            },
                            icon  = { Icon(item.icon, contentDescription = label) },
                            label = { Text(label) }
                        )
                    }
                }
            }
        }
    ) { padding ->
        NavHost(
            navController    = navController,
            startDestination = startDestination,
            modifier         = Modifier.padding(padding)
        ) {
            composable("login") {
                LoginScreen(
                    onLoginSuccess = {
                        navController.navigate("home") {
                            popUpTo("login") { inclusive = true }
                        }
                    }
                )
            }
            composable("home") {
                HomeScreen(
                    onLogout = {
                        scope.launch {
                            authRepository.logout()
                            navController.navigate("login") {
                                popUpTo(0) { inclusive = true }
                            }
                        }
                    }
                )
            }
            composable("today")    { TodayScreen() }
            composable("voice")    { VoiceAssistantScreen() }
            composable("games")    { GamesScreen() }
            composable("memories") { MemoriesScreen() }
            composable("profile") {
                ProfileScreen(
                    onLoggedOut = {
                        navController.navigate("login") {
                            popUpTo(0) { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}
