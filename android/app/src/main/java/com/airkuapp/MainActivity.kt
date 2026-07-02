package com.airkuapp

import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.airkuapp.ui.AirQualityViewModel
import com.airkuapp.ui.BottomTab
import com.airkuapp.ui.SensorConnectionState
import com.airkuapp.ui.screens.DashboardScreen
import com.airkuapp.ui.screens.HistoryScreen
import com.airkuapp.ui.screens.SettingsScreen
import com.airkuapp.ui.screens.TrendsScreen
import com.airkuapp.ui.theme.MyApplicationTheme

class MainActivity : ComponentActivity() {

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        // Handle runtime permission response if needed
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Request POST_NOTIFICATIONS permission dynamically on startup for Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    android.Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        setContent {
            val viewModel: AirQualityViewModel = viewModel()
            val appSettings by viewModel.appSettings.collectAsState()
            val currentTab by viewModel.currentTab.collectAsState()
            val connectionState by viewModel.connectionState.collectAsState()

            val isDarkMode = if (appSettings.enableAdaptiveTheme) {
                val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
                hour < 6 || hour >= 18 // Dark mode from 6 PM to 6 AM
            } else {
                appSettings.isDarkMode
            }

            MyApplicationTheme(darkTheme = isDarkMode) {
                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    topBar = {
                        TopBar(currentTab = currentTab, connectionState = connectionState)
                    },
                    bottomBar = {
                        BottomNavigationBar(currentTab = currentTab, onTabSelected = { viewModel.selectTab(it) })
                    }
                ) { innerPadding ->
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(MaterialTheme.colorScheme.background)
                            .padding(innerPadding)
                    ) {
                        val screenModifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp)

                        when (currentTab) {
                            BottomTab.Dashboard -> DashboardScreen(viewModel = viewModel, modifier = screenModifier)
                            BottomTab.Trends -> TrendsScreen(viewModel = viewModel, modifier = screenModifier)
                            BottomTab.History -> HistoryScreen(viewModel = viewModel, modifier = screenModifier)
                            BottomTab.Settings -> SettingsScreen(viewModel = viewModel, modifier = screenModifier)
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TopBar(
    currentTab: BottomTab,
    connectionState: SensorConnectionState
) {
    val title = when (currentTab) {
        BottomTab.Dashboard -> "Airku"
        BottomTab.Trends -> "Tren & Analisis AI"
        BottomTab.History -> "Riwayat"
        BottomTab.Settings -> "Pengaturan"
    }

    CenterAlignedTopAppBar(
        title = {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.primary
                )
            }
        },
        navigationIcon = {
            Icon(
                imageVector = Icons.Default.Cloud,
                contentDescription = "Cloud Icon",
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(start = 16.dp)
            )
        },
        actions = {
            Box(modifier = Modifier.padding(end = 16.dp)) {
                val (connectionIcon, connectionColor) = when (connectionState) {
                    SensorConnectionState.Connected -> Icons.Default.Wifi to Color(0xFF2CCB7B)
                    SensorConnectionState.Disconnected -> Icons.Default.WifiOff to Color.Gray
                    SensorConnectionState.Connecting -> Icons.Default.Cached to Color(0xFFFFC107)
                }
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier.size(40.dp)
                ) {
                    Icon(
                        imageVector = connectionIcon,
                        contentDescription = "Connection Status",
                        tint = connectionColor,
                        modifier = Modifier.size(24.dp)
                    )
                    if (connectionState == SensorConnectionState.Connected) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .align(Alignment.TopEnd)
                                .background(Color(0xFF2CCB7B), CircleShape)
                        )
                    }
                }
            }
        },
        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerLowest
        )
    )
}

@Composable
fun BottomNavigationBar(
    currentTab: BottomTab,
    onTabSelected: (BottomTab) -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
            .border(
                width = 1.dp,
                color = Color.White.copy(alpha = 0.25f), // subtle white border outline
                shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp)
            ),
        tonalElevation = 12.dp,
        color = MaterialTheme.colorScheme.surfaceContainerLowest
    ) {
        NavigationBar(
            containerColor = Color.Transparent,
            modifier = Modifier.fillMaxWidth()
        ) {
            NavigationBarItem(
                selected = currentTab == BottomTab.Dashboard,
                onClick = { onTabSelected(BottomTab.Dashboard) },
                icon = { Icon(Icons.Default.Dashboard, contentDescription = "Dashboard") },
                label = { Text("Dashboard", style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.primary,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                )
            )

            NavigationBarItem(
                selected = currentTab == BottomTab.Trends,
                onClick = { onTabSelected(BottomTab.Trends) },
                icon = { Icon(Icons.Default.TrendingUp, contentDescription = "Trends") },
                label = { Text("Trends", style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.primary,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                )
            )

            NavigationBarItem(
                selected = currentTab == BottomTab.History,
                onClick = { onTabSelected(BottomTab.History) },
                icon = { Icon(Icons.Default.History, contentDescription = "History") },
                label = { Text("History", style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.primary,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                )
            )

            NavigationBarItem(
                selected = currentTab == BottomTab.Settings,
                onClick = { onTabSelected(BottomTab.Settings) },
                icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                label = { Text("Settings", style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.primary,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                )
            )
        }
    }
}
