package com.airkuapp.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.airkuapp.data.AppDatabase
import kotlinx.coroutines.flow.firstOrNull
import java.util.Calendar

class WeeklyReportWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        val database = AppDatabase.getDatabase(context)
        val settings = database.airQualityDao().getSettingsSync()

        if (settings == null || !settings.enableWeeklyReport) {
            return Result.success()
        }

        // Calculate time range (Last 7 days)
        val calendar = Calendar.getInstance()
        val endTime = calendar.timeInMillis
        calendar.add(Calendar.DAY_OF_YEAR, -7)
        val startTime = calendar.timeInMillis

        // Retrieve all logs (Simplified for this version, usually we'd filter in SQL)
        val allLogs = database.airQualityDao().getAllLogs().firstOrNull() ?: emptyList()
        
        val weeklyLogs = allLogs.filter { it.timestamp in startTime..endTime }
        
        if (weeklyLogs.isEmpty()) {
            sendNotification("Laporan Mingguan AirKu", "Tidak ada data polusi udara yang terkumpul minggu ini.")
            return Result.success()
        }

        // Calculate Average AQI
        val avgAqi = weeklyLogs.map { it.aqi }.average().toInt()
        
        val status = when {
            avgAqi <= 50 -> "Sangat Sehat 🌿"
            avgAqi <= 100 -> "Cukup Baik 🌤️"
            else -> "Buruk 😷"
        }

        val message = "Rata-rata AQI 7 hari terakhir adalah $avgAqi ($status). Anda memiliki ${weeklyLogs.size} rekaman data minggu ini."
        sendNotification("Laporan Mingguan Kualitas Udara", message)

        return Result.success()
    }

    private fun sendNotification(title: String, message: String) {
        val channelId = "air_quality_weekly_report"
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Laporan Mingguan",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            notificationManager.createNotificationChannel(channel)
        }

        val builder = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_menu_today)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)

        notificationManager.notify(7777, builder.build())
    }
}
