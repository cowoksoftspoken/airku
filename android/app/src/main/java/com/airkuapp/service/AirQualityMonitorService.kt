package com.airkuapp.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.airkuapp.data.AirQualityApiService
import com.airkuapp.data.AirQualityLog
import com.airkuapp.data.AppDatabase
import com.airkuapp.data.AppSettings
import kotlinx.coroutines.*
import com.airkuapp.data.ApiClient
import com.airkuapp.data.RoomReading
import java.util.concurrent.TimeUnit

class AirQualityMonitorService : Service() {

    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)
    
    private val CHANNEL_ID = "air_quality_monitor_channel"
    private val NOTIFICATION_ID = 1001

    private lateinit var database: AppDatabase

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getDatabase(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createForegroundNotification("Memantau kualitas udara...")
        startForeground(NOTIFICATION_ID, notification)

        startMonitoring()

        return START_STICKY
    }

    private fun startMonitoring() {
        serviceScope.launch {
            while (isActive) {
                try {
                    val settings = database.airQualityDao().getSettingsSync() ?: AppSettings()
                    
                    if (!settings.enableBackgroundMonitoring) {
                        stopSelf()
                        return@launch
                    }

                    if (settings.enableSimulation) {
                        // Skip polling if simulation
                        delay(TimeUnit.MINUTES.toMillis(5))
                        continue
                    }

                    val baseUrl = if (settings.connectionMode == "direct") {
                        settings.sensorIp
                    } else {
                        settings.backendUrl
                    }

                    val apiService = ApiClient.getService(baseUrl)

                    val reading: RoomReading? = try {
                        if (settings.connectionMode == "direct") {
                            apiService.getDirectReading()
                        } else {
                            val list = apiService.getBackendReadings()
                            list.firstOrNull()
                        }
                    } catch (e: Exception) {
                        null
                    }

                    if (reading != null) {
                        val aqi = reading.aqi
                        
                        val status = when {
                            aqi <= 50 -> "Baik"
                            aqi <= 100 -> "Sedang"
                            else -> "Buruk"
                        }
                        
                        val log = AirQualityLog(
                            timestamp = reading.timestamp ?: System.currentTimeMillis(),
                            aqi = aqi,
                            temperature = reading.temperature,
                            humidity = reading.humidity,
                            pm25 = reading.pm25,
                            pm10 = reading.pm10,
                            co2 = reading.co2,
                            voc = reading.voc,
                            location = "Background Monitor",
                            status = status
                        )
                        database.airQualityDao().insertLog(log)
                        
                        updateForegroundNotification("AQI Terakhir: $aqi ($status)")
                        
                        if (settings.enableAirQualityWarning && aqi > 100) {
                            sendWarningNotification(aqi)
                        }
                    }
                } catch (e: Exception) {
                    updateForegroundNotification("Gagal terhubung ke sensor.")
                }
                
                // Poll every 5 minutes
                delay(TimeUnit.MINUTES.toMillis(5))
            }
        }
    }

    private fun createForegroundNotification(contentText: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AirKu Background Monitor")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateForegroundNotification(contentText: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notification = createForegroundNotification(contentText)
        notificationManager.notify(NOTIFICATION_ID, notification)
    }
    
    private fun sendWarningNotification(aqiValue: Int) {
        val warningChannelId = "air_quality_warning_channel"
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                warningChannelId,
                "Peringatan Kualitas Udara",
                NotificationManager.IMPORTANCE_HIGH
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        val builder = NotificationCompat.Builder(this, warningChannelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("⚠️ Peringatan Kualitas Udara Buruk!")
            .setContentText("AQI saat ini mencapai tingkat Buruk ($aqiValue).")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)

        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(4243, builder.build())
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_ID,
                "Air Quality Background Monitor",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(serviceChannel)
        }
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceJob.cancel()
    }
}
