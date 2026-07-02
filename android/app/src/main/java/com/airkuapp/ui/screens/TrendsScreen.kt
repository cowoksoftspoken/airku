package com.airkuapp.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.airkuapp.ui.AirQualityViewModel

@Composable
fun TrendsScreen(
    viewModel: AirQualityViewModel,
    modifier: Modifier = Modifier
) {
    val pm25 by viewModel.pm25.collectAsState()
    val pm10 by viewModel.pm10.collectAsState()
    val co2 by viewModel.co2.collectAsState()
    val voc by viewModel.voc.collectAsState()
    val allLogs by viewModel.allLogs.collectAsState()

    val scrollState = rememberScrollState()

    var selectedRange by remember { androidx.compose.runtime.mutableStateOf("Hari ini") }
    
    val filteredLogs = remember(allLogs, selectedRange) {
        val now = System.currentTimeMillis()
        val timeLimit = when (selectedRange) {
            "Hari ini" -> now - (24L * 60 * 60 * 1000)
            "7 hari" -> now - (7L * 24 * 60 * 60 * 1000)
            "30 hari" -> now - (30L * 24 * 60 * 60 * 1000)
            else -> 0L
        }
        allLogs.filter { it.timestamp >= timeLimit }
    }
    
    val recentLogs = filteredLogs.takeLast(6)

    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(scrollState)
            .padding(vertical = 16.dp),
        verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(16.dp)
    ) {
        // Title
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "Tren Kualitas Udara",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Analisis data real-time sensor IoT Anda",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Time Range Selector
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.surfaceContainerLow, shape = RoundedCornerShape(12.dp))
                .padding(4.dp)
        ) {
            listOf("Hari ini", "7 hari", "30 hari").forEach { range ->
                val isSelected = selectedRange == range
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(8.dp))
                        .background(if (isSelected) MaterialTheme.colorScheme.primary else Color.Transparent)
                        .clickableWithoutRipple { selectedRange = range }
                        .padding(vertical = 8.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = range,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                        color = if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // AQI Fluctuation Chart Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val chartTitle = when (selectedRange) {
                        "Hari ini" -> "FLUKTUASI AQI 24 JAM TERAKHIR"
                        "7 hari" -> "FLUKTUASI AQI 7 HARI TERAKHIR"
                        "30 hari" -> "FLUKTUASI AQI 30 HARI TERAKHIR"
                        else -> "FLUKTUASI AQI"
                    }
                    Text(
                        text = chartTitle,
                        style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 1.sp),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .background(Color(0xFF2CCB7B), RoundedCornerShape(50))
                        )
                        Text(
                            text = "Baik",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color(0xFF2CCB7B),
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Smooth Bezier Curve Canvas
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                ) {
                    if (filteredLogs.isEmpty()) {
                        Text(
                            text = "Belum ada data untuk periode ini.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.align(Alignment.Center)
                        )
                    } else {
                        Canvas(modifier = Modifier.fillMaxSize()) {
                            val width = size.width
                            val height = size.height

                            // Draw Grid Horizontal Lines
                            drawLine(
                                color = Color.LightGray.copy(alpha = 0.15f),
                                start = androidx.compose.ui.geometry.Offset(0f, height * 0.25f),
                                end = androidx.compose.ui.geometry.Offset(width, height * 0.25f),
                                strokeWidth = 1.dp.toPx()
                            )
                            drawLine(
                                color = Color.LightGray.copy(alpha = 0.15f),
                                start = androidx.compose.ui.geometry.Offset(0f, height * 0.5f),
                                end = androidx.compose.ui.geometry.Offset(width, height * 0.5f),
                                strokeWidth = 1.dp.toPx()
                            )
                            drawLine(
                                color = Color.LightGray.copy(alpha = 0.15f),
                                start = androidx.compose.ui.geometry.Offset(0f, height * 0.75f),
                                end = androidx.compose.ui.geometry.Offset(width, height * 0.75f),
                                strokeWidth = 1.dp.toPx()
                            )

                            // Calculate dynamic points from recentLogs
                            val maxAqi = 200f // Assume max AQI scale is 200
                            val points = if (recentLogs.size >= 2) {
                                recentLogs.mapIndexed { index, log ->
                                    val x = (width / (recentLogs.size - 1)) * index
                                    // y is inverted (0 is top, height is bottom)
                                    val normalizedAqi = (log.aqi.toFloat() / maxAqi).coerceIn(0f, 1f)
                                    val y = height - (height * normalizedAqi)
                                    androidx.compose.ui.geometry.Offset(x, y)
                                }
                            } else {
                                // Flat line if not enough data
                                listOf(
                                    androidx.compose.ui.geometry.Offset(0f, height * 0.8f),
                                    androidx.compose.ui.geometry.Offset(width, height * 0.8f)
                                )
                            }

                            val path = Path().apply {
                                moveTo(points[0].x, points[0].y)
                                if (points.size > 2) {
                                    for (i in 0 until points.size - 1) {
                                        val p0 = points[i]
                                        val p1 = points[i + 1]
                                        val controlX = (p0.x + p1.x) / 2
                                        cubicTo(controlX, p0.y, controlX, p1.y, p1.x, p1.y)
                                    }
                                } else {
                                    lineTo(points[1].x, points[1].y)
                                }
                            }

                            // Gradient Area Path
                            val fillPath = Path().apply {
                                addPath(path)
                                lineTo(width, height)
                                lineTo(0f, height)
                                close()
                            }

                            // Draw Filled Area
                            drawPath(
                                path = fillPath,
                                brush = Brush.verticalGradient(
                                    colors = listOf(
                                        Color(0xFF2CCB7B).copy(alpha = 0.25f),
                                        Color(0xFF2CCB7B).copy(alpha = 0.0f)
                                    )
                                )
                            )

                            // Draw Curve Line
                            drawPath(
                                path = path,
                                color = Color(0xFF2CCB7B),
                                style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round)
                            )

                            // Highlight the latest point
                            drawCircle(
                                color = Color(0xFF2CCB7B),
                                radius = 5.dp.toPx(),
                                center = points.last()
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    if (recentLogs.size >= 2) {
                        val formatter = java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault())
                        recentLogs.forEachIndexed { index, log ->
                            val label = if (index == recentLogs.size - 1) "Sekarang" else formatter.format(java.util.Date(log.timestamp))
                            Text(
                                text = label,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    } else {
                        Text(
                            text = "Simpan data dari Dashboard untuk melihat grafik",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                        )
                    }
                }
            }
        }

        // Pollutant Breakdown & Warning bento-row
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(bottom = 16.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Analytics,
                        contentDescription = "Breakdown Polutan",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Text(
                        text = "Breakdown Polutan",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                // PM2.5 Progress
                PollutantBar(name = "PM2.5", valueText = "$pm25 µg/m³", progress = (pm25 / 100f).coerceIn(0f, 1f), color = Color(0xFF2CCB7B))
                Spacer(modifier = Modifier.height(16.dp))

                // PM10 Progress
                PollutantBar(name = "PM10", valueText = "$pm10 µg/m³", progress = (pm10 / 150f).coerceIn(0f, 1f), color = Color(0xFF2CCB7B))
                Spacer(modifier = Modifier.height(16.dp))

                // CO2 Progress (high indicator)
                PollutantBar(name = "CO2", valueText = "$co2 ppm", progress = (co2 / 1000f).coerceIn(0f, 1f), color = Color(0xFFF79F0E))
                Spacer(modifier = Modifier.height(16.dp))

                // VOC Progress
                PollutantBar(name = "VOC", valueText = String.format("%.1f mg/m³", voc), progress = (voc / 1.0).toFloat().coerceIn(0f, 1f), color = Color(0xFF2CCB7B))
            }
        }

        // Pollution Peak Warning Card
        val peakLog = filteredLogs.maxByOrNull { it.aqi }
        if (peakLog != null && peakLog.aqi > 50) {
            val formatter = java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault())
            val timeStr = formatter.format(java.util.Date(peakLog.timestamp))
            val pollutantSource = when {
                peakLog.pm25 > 50 -> "partikel debu halus atau asap (PM2.5 tinggi)"
                peakLog.pm10 > 100 -> "debu kasar atau konstruksi (PM10 tinggi)"
                peakLog.co2 > 1000 -> "sirkulasi udara yang buruk (CO2 tinggi)"
                peakLog.voc > 0.5 -> "bahan kimia pembersih atau cat (VOC tinggi)"
                else -> "kualitas udara sekitar yang memburuk"
            }
            
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.08f)
                ),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.15f))
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Box(
                        modifier = Modifier
                            .background(MaterialTheme.colorScheme.error.copy(alpha = 0.15f), RoundedCornerShape(12.dp))
                            .padding(10.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = "Puncak polusi terdeteksi",
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                    Column {
                        Text(
                            text = "Puncak polusi terdeteksi",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.error
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Puncak polusi mencapai AQI ${peakLog.aqi} pada pukul $timeStr — kemungkinan dari $pollutantSource.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            lineHeight = 20.sp
                        )
                    }
                }
            }
        }

        // Comprehensive AI Analysis Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.1f)
            ),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.2f))
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.padding(bottom = 12.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .background(Color(0xFF006D3D).copy(alpha = 0.15f), RoundedCornerShape(12.dp))
                            .padding(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = "Analisis TFLite On-Device (Lokal)",
                            tint = Color(0xFF006D3D),
                            modifier = Modifier.size(24.dp)
                        )
                    }
                    Text(
                        text = "Analisis AI",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = Color(0xFF006D3D),
                        modifier = Modifier.weight(1f)
                    )
                    
                    val isAiLoading by viewModel.isRecommendationLoading.collectAsState()
                    
                    // Live AI Refresh button
                    IconButton(
                        onClick = { viewModel.fetchAiRecommendation() },
                        enabled = !isAiLoading,
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Perbarui Analisis TFLite",
                            tint = Color(0xFF006D3D),
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }

                val aiRecommendation by viewModel.aiRecommendation.collectAsState()
                val isAiLoading by viewModel.isRecommendationLoading.collectAsState()
                
                if (isAiLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier
                            .align(Alignment.CenterHorizontally)
                            .size(36.dp)
                            .padding(8.dp),
                        color = Color(0xFF006D3D)
                    )
                } else {
                    Text(
                        text = aiRecommendation,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        lineHeight = 22.sp
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    val aqi by viewModel.aqi.collectAsState()
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .background(Color(0xFF006D3D).copy(alpha = 0.05f), RoundedCornerShape(12.dp))
                            .padding(12.dp)
                    ) {
                        Text(text = "PREDIKSI BESOK", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f))
                        Spacer(modifier = Modifier.height(4.dp))
                        val prediksi = when {
                            aqi <= 50 -> "Kualitas Baik"
                            aqi <= 100 -> "Kualitas Sedang"
                            else -> "Kualitas Buruk"
                        }
                        Text(text = prediksi, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = Color(0xFF006D3D))
                    }

                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .background(Color(0xFF006D3D).copy(alpha = 0.05f), RoundedCornerShape(12.dp))
                            .padding(12.dp)
                    ) {
                        Text(text = "SARAN FILTER", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f))
                        Spacer(modifier = Modifier.height(4.dp))
                        val pm25 by viewModel.pm25.collectAsState()
                        val saranFilter = if (pm25 > 35) "Perlu Dibersihkan" else "Masih Optimal"
                        Text(text = saranFilter, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
fun PollutantBar(
    name: String,
    valueText: String,
    progress: Float,
    color: Color
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = name,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = valueText,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold
            )
        }
        Spacer(modifier = Modifier.height(6.dp))
        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(50)),
            color = color,
            trackColor = MaterialTheme.colorScheme.surfaceVariant
        )
    }
}

@Composable
fun Modifier.clickableWithoutRipple(onClick: () -> Unit): Modifier {
    return this.clickable(
        interactionSource = remember { androidx.compose.foundation.interaction.MutableInteractionSource() },
        indication = null,
        onClick = onClick
    )
}
