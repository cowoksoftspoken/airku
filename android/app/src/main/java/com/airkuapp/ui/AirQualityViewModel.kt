package com.airkuapp.ui

import android.app.Application
import android.os.Build
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.airkuapp.data.AirQualityLog
import com.airkuapp.data.AirQualityRepository
import com.airkuapp.data.AppDatabase
import com.airkuapp.data.AppSettings
import com.airkuapp.data.LocalTfLiteService
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlin.random.Random

enum class BottomTab {
    Dashboard, Trends, History, Settings
}

enum class SensorConnectionState {
    Disconnected, Connecting, Connected
}

class AirQualityViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: AirQualityRepository

    // Navigation and UI States
    private val _currentTab = MutableStateFlow(BottomTab.Dashboard)
    val currentTab: StateFlow<BottomTab> = _currentTab.asStateFlow()

    // Sensor Readings State
    private val _aqi = MutableStateFlow(0)
    val aqi: StateFlow<Int> = _aqi.asStateFlow()

    private val _temperature = MutableStateFlow(0.0)
    val temperature: StateFlow<Double> = _temperature.asStateFlow()

    private val _humidity = MutableStateFlow(0)
    val humidity: StateFlow<Int> = _humidity.asStateFlow()

    private val _pm25 = MutableStateFlow(0)
    val pm25: StateFlow<Int> = _pm25.asStateFlow()

    private val _pm10 = MutableStateFlow(0)
    val pm10: StateFlow<Int> = _pm10.asStateFlow()

    private val _co2 = MutableStateFlow(0)
    val co2: StateFlow<Int> = _co2.asStateFlow()

    private val _voc = MutableStateFlow(0.0)
    val voc: StateFlow<Double> = _voc.asStateFlow()

    private val _aiRecommendation = MutableStateFlow(
        "Menunggu data sensor..."
    )
    val aiRecommendation: StateFlow<String> = _aiRecommendation.asStateFlow()

    private val _isRecommendationLoading = MutableStateFlow(false)
    val isRecommendationLoading: StateFlow<Boolean> = _isRecommendationLoading.asStateFlow()

    private var lastSensorTimestamp: Long? = null

    // Room Monitoring State
    private val _currentRoom = MutableStateFlow("Ruang Kelas A")
    val currentRoom: StateFlow<String> = _currentRoom.asStateFlow()

    private val _rooms = MutableStateFlow(listOf(
        "Ruang Kelas A", 
        "Ruang Kelas B", 
        "Kamar Tidur Utama", 
        "Ruang Tamu", 
        "Ruang Meeting Kantor"
    ))
    val rooms: StateFlow<List<String>> = _rooms.asStateFlow()

    // Network & Backend Communication States
    private val _networkError = MutableStateFlow<String?>(null)
    val networkError: StateFlow<String?> = _networkError.asStateFlow()

    private val _backendReadings = MutableStateFlow<List<com.airkuapp.data.RoomReading>>(emptyList())
    val backendReadings: StateFlow<List<com.airkuapp.data.RoomReading>> = _backendReadings.asStateFlow()

    val allDeviceMappings: StateFlow<List<com.airkuapp.data.DeviceMapping>>

    fun saveDeviceMapping(espId: String, customName: String, ipAddress: String) {
        viewModelScope.launch {
            repository.insertDeviceMapping(com.airkuapp.data.DeviceMapping(espId, customName, ipAddress))
            val settings = appSettings.value
            if (settings.connectionMode == "backend") {
                fetchBackendReadings(settings.backendUrl)
            }
        }
    }

    fun deleteDeviceMapping(espId: String) {
        viewModelScope.launch {
            repository.deleteDeviceMapping(espId)
            val settings = appSettings.value
            if (settings.connectionMode == "backend") {
                fetchBackendReadings(settings.backendUrl)
            }
        }
    }

    fun scanForDevices() {
        viewModelScope.launch {
            _isScanning.value = true
            val devices = com.airkuapp.data.UdpDiscoveryService.discoverDevices()
            _discoveredDevices.value = devices
            _isScanning.value = false
        }
    }

    fun selectRoom(roomName: String) {
        _currentRoom.value = roomName
        val settings = appSettings.value

        if (settings.connectionMode == "backend") {
            val currentReading = _backendReadings.value.firstOrNull { it.room == roomName }
            if (currentReading != null) {
                _aqi.value = currentReading.aqi
                _temperature.value = currentReading.temperature
                _humidity.value = currentReading.humidity
                _pm25.value = currentReading.pm25
                _pm10.value = currentReading.pm10
                _co2.value = currentReading.co2
                _voc.value = currentReading.voc
                fetchAiRecommendation()
            }
        } else if (settings.connectionMode == "simulated") {
            // Simulating different localized environments for each room
            when (roomName) {
                "Ruang Kelas A" -> {
                    _aqi.value = 42
                    _temperature.value = 24.5
                    _humidity.value = 62
                    _pm25.value = 12
                    _pm10.value = 34
                    _co2.value = 410
                    _voc.value = 0.2
                }
                "Ruang Kelas B" -> {
                    _aqi.value = 85
                    _temperature.value = 26.2
                    _humidity.value = 68
                    _pm25.value = 28
                    _pm10.value = 52
                    _co2.value = 840
                    _voc.value = 0.45
                }
                "Kamar Tidur Utama" -> {
                    _aqi.value = 24
                    _temperature.value = 22.0
                    _humidity.value = 54
                    _pm25.value = 6
                    _pm10.value = 18
                    _co2.value = 390
                    _voc.value = 0.08
                }
                "Ruang Tamu" -> {
                    _aqi.value = 58
                    _temperature.value = 25.1
                    _humidity.value = 58
                    _pm25.value = 16
                    _pm10.value = 40
                    _co2.value = 490
                    _voc.value = 0.15
                }
                "Ruang Meeting Kantor" -> {
                    _aqi.value = 112
                    _temperature.value = 23.8
                    _humidity.value = 61
                    _pm25.value = 42
                    _pm10.value = 75
                    _co2.value = 1150
                    _voc.value = 0.62
                }
            }
            fetchAiRecommendation()
        }
    }

    // IoT Sensor connection state
    private val _connectionState = MutableStateFlow(SensorConnectionState.Disconnected)
    val connectionState: StateFlow<SensorConnectionState> = _connectionState.asStateFlow()

    private val _discoveredDevices = MutableStateFlow<List<com.airkuapp.data.DiscoveredDevice>>(emptyList())
    val discoveredDevices: StateFlow<List<com.airkuapp.data.DiscoveredDevice>> = _discoveredDevices.asStateFlow()

    private val _isScanning = MutableStateFlow(false)
    val isScanning: StateFlow<Boolean> = _isScanning.asStateFlow()

    // Filter states
    private val _historyFilter = MutableStateFlow("Semua")
    val historyFilter: StateFlow<String> = _historyFilter.asStateFlow()

    private val _trendsRange = MutableStateFlow("Hari ini")
    val trendsRange: StateFlow<String> = _trendsRange.asStateFlow()

    // Settings flows
    val appSettings: StateFlow<AppSettings>
    val allLogs: StateFlow<List<AirQualityLog>>

    // Keep track of the last 12 readings for the LSTM model
    private val readingHistory = mutableListOf<FloatArray>()
    private var tfLiteService: com.airkuapp.data.LocalTfLiteService? = null

    private var lastNotificationTime = 0L
    private var _lastAiStatus = "Sedang"
    private var _lastAiAnomaly = false

    init {
        val database = AppDatabase.getDatabase(application)
        repository = AirQualityRepository(database.airQualityDao())
        
        tfLiteService = com.airkuapp.data.LocalTfLiteService(application)

        createNotificationChannel()

        // Expose Settings Flow
        appSettings = repository.appSettings
            .map { it ?: AppSettings() }
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5000),
                initialValue = AppSettings()
            )

        // Expose Logs Flow
        allLogs = repository.allLogs
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5000),
                initialValue = emptyList()
            )

        // Expose Device Mappings Flow
        allDeviceMappings = repository.allDeviceMappings
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5000),
                initialValue = emptyList()
            )

        // Initialize DB asynchronously
        viewModelScope.launch {
            repository.initializeDatabaseIfEmpty()
            // Start the service if enabled when the app launches
            val initialSettings = database.airQualityDao().getSettingsSync() ?: AppSettings()
            updateServiceState(initialSettings.enableBackgroundMonitoring)
            updateWeeklyReportState(initialSettings.enableWeeklyReport)
        }

        // Periodic telemetry fetch / simulation loop
        viewModelScope.launch {
            while (true) {
                val settings = appSettings.value
                if (settings.enableSimulation) {
                    _networkError.value = null
                    _connectionState.value = SensorConnectionState.Connected
                    fluctuateMockValues()
                } else {
                    if (_connectionState.value == SensorConnectionState.Connected) {
                        when (settings.connectionMode) {
                            "direct" -> {
                                fetchDirectReading(settings.sensorIp)
                            }
                            "backend" -> {
                                fetchBackendReadings(settings.backendUrl)
                            }
                        }
                    }
                }
                delay(10000) // Update every 10 seconds
            }
        }
    }

    private fun fluctuateMockValues() {
        if (_aqi.value == 0) {
            _aqi.value = 45
            _temperature.value = 25.0
            _humidity.value = 60
            _pm25.value = 15
            _pm10.value = 35
            _co2.value = 450
            _voc.value = 0.2
        }

        val deltaAqi = Random.nextInt(-4, 5)
        _aqi.value = (_aqi.value + deltaAqi).coerceIn(15, 185)

        val deltaTemp = Random.nextDouble(-0.3, 0.4)
        _temperature.value = (_temperature.value + deltaTemp).coerceIn(20.0, 35.0)

        val deltaHum = Random.nextInt(-2, 3)
        _humidity.value = (_humidity.value + deltaHum).coerceIn(40, 95)

        val deltaPm25 = Random.nextInt(-3, 4)
        _pm25.value = (_pm25.value + deltaPm25).coerceIn(5, 120)

        val deltaPm10 = Random.nextInt(-4, 5)
        _pm10.value = (_pm10.value + deltaPm10).coerceIn(10, 150)

        val deltaCo2 = Random.nextInt(-15, 16)
        _co2.value = (_co2.value + deltaCo2).coerceIn(350, 1100)

        val deltaVoc = Random.nextDouble(-0.02, 0.03)
        _voc.value = (_voc.value + deltaVoc).coerceIn(0.01, 1.2)

        if (_aqi.value > 100) {
            checkAndSendAirQualityWarning()
        }
    }

    private suspend fun fetchDirectReading(ip: String) {
        if (ip.trim().isEmpty()) {
            _networkError.value = "Alamat IP belum dikonfigurasi di Pengaturan"
            _connectionState.value = SensorConnectionState.Disconnected
            return
        }

        try {
            _networkError.value = null
            _connectionState.value = SensorConnectionState.Connecting
            val service = com.airkuapp.data.ApiClient.getService(ip)
            val reading = service.getDirectReading()

            _aqi.value = reading.aqi
            _temperature.value = reading.temperature
            _humidity.value = reading.humidity
            _pm25.value = reading.pm25
            _pm10.value = reading.pm10
            _co2.value = reading.co2
            _voc.value = reading.voc
            lastSensorTimestamp = reading.timestamp

            _rooms.value = listOf(reading.room)
            _currentRoom.value = reading.room

            _connectionState.value = SensorConnectionState.Connected
            fetchAiRecommendation()

            if (reading.aqi > 100) {
                checkAndSendAirQualityWarning()
            }
        } catch (e: Exception) {
            _networkError.value = "Gagal terhubung ke ESP32 (${e.localizedMessage ?: "Network Timeout"})"
            _connectionState.value = SensorConnectionState.Disconnected
        }
    }

    private suspend fun fetchBackendReadings(url: String) {
        if (url.trim().isEmpty()) {
            _networkError.value = "URL Backend belum dikonfigurasi"
            _connectionState.value = SensorConnectionState.Disconnected
            return
        }

        try {
            _connectionState.value = SensorConnectionState.Connecting
            val service = com.airkuapp.data.ApiClient.getService(url)
            val readings = service.getBackendReadings()

            _networkError.value = null

            val currentMappings = allDeviceMappings.value
            val mappedReadings = readings.map { reading ->
                val mapping = currentMappings.firstOrNull { it.espId == reading.espId }
                if (mapping != null && mapping.customName.isNotEmpty()) {
                    reading.copy(room = mapping.customName)
                } else {
                    reading
                }
            }

            _backendReadings.value = mappedReadings
            _connectionState.value = SensorConnectionState.Connected

            if (mappedReadings.isNotEmpty()) {
                val fetchedRooms = mappedReadings.map { it.room }.distinct()
                _rooms.value = fetchedRooms

                var current = currentRoom.value
                if (current !in fetchedRooms) {
                    current = fetchedRooms.first()
                    _currentRoom.value = current
                }

                val currentReading = mappedReadings.firstOrNull { it.room == current }
                if (currentReading != null) {
                    _aqi.value = currentReading.aqi
                    _temperature.value = currentReading.temperature
                    _humidity.value = currentReading.humidity
                    _pm25.value = currentReading.pm25
                    _pm10.value = currentReading.pm10
                    _co2.value = currentReading.co2
                    _voc.value = currentReading.voc
                    lastSensorTimestamp = currentReading.timestamp

                    fetchAiRecommendation()
                    if (currentReading.aqi > 100) {
                        checkAndSendAirQualityWarning()
                    }
                }
            } else {
                _rooms.value = emptyList()
                _networkError.value = "Koneksi sukses, namun belum ada data ESP32 terdaftar di backend"
            }
        } catch (e: Exception) {
            val errString = e.message ?: e.javaClass.simpleName
            _networkError.value = "Gagal menghubungi Backend: $errString"
            _connectionState.value = SensorConnectionState.Disconnected
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Peringatan Kualitas Udara"
            val descriptionText = "Notifikasi ketika kualitas udara memburuk"
            val importance = android.app.NotificationManager.IMPORTANCE_HIGH
            val channel = android.app.NotificationChannel("air_quality_channel", name, importance).apply {
                description = descriptionText
            }
            val notificationManager: android.app.NotificationManager =
                getApplication<Application>().getSystemService(android.content.Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    fun checkAndSendAirQualityWarning(isAnomaly: Boolean = false) {
        val settings = appSettings.value
        if (!settings.enableAirQualityWarning) return

        val currentAqi = _aqi.value
        if (currentAqi <= 100 && !isAnomaly) return

        val currentTime = System.currentTimeMillis()
        // Anti-spam: wait at least 3 minutes (180,000 ms)
        if (currentTime - lastNotificationTime < 180000) {
            return
        }

        sendNotification(currentAqi, isAnomaly)
        lastNotificationTime = currentTime
    }

    private fun sendNotification(aqiValue: Int, isAnomaly: Boolean) {
        val context = getApplication<Application>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (androidx.core.content.ContextCompat.checkSelfPermission(
                    context,
                    android.Manifest.permission.POST_NOTIFICATIONS
                ) != android.content.pm.PackageManager.PERMISSION_GRANTED
            ) {
                return
            }
        }

        val title = if (isAnomaly) "⚠️ Peringatan Anomali Sensor!" else "⚠️ Peringatan Kualitas Udara Buruk!"
        val message = if (isAnomaly) "Terdeteksi pola sensor tidak wajar. Periksa alat Anda segera atau pastikan tidak ada bahan kimia berdekatan." else "Kualitas udara saat ini mencapai tingkat Buruk (AQI $aqiValue). Harap tutup jendela atau hidupkan pemurni udara Anda."

        val builder = androidx.core.app.NotificationCompat.Builder(context, "air_quality_channel")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(message)
            .setPriority(androidx.core.app.NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)

        val notificationManager = androidx.core.app.NotificationManagerCompat.from(context)
        try {
            notificationManager.notify(4242, builder.build())
        } catch (e: SecurityException) {
            // Permission not granted
        }
    }

    fun selectTab(tab: BottomTab) {
        _currentTab.value = tab
    }

    fun setHistoryFilter(filter: String) {
        _historyFilter.value = filter
    }

    fun setTrendsRange(range: String) {
        _trendsRange.value = range
    }

    fun connectSensor(address: String) {
        viewModelScope.launch {
            _connectionState.value = SensorConnectionState.Connecting
            val settings = appSettings.value
            if (settings.enableSimulation) {
                delay(1000)
                _connectionState.value = SensorConnectionState.Connected
            } else {
                if (settings.connectionMode == "direct") {
                    fetchDirectReading(address)
                } else if (settings.connectionMode == "backend") {
                    fetchBackendReadings(address)
                }
            }
        }
    }

    fun disconnectSensor() {
        _connectionState.value = SensorConnectionState.Disconnected
        _aqi.value = 0
        _temperature.value = 0.0
        _humidity.value = 0
        _pm25.value = 0
        _pm10.value = 0
        _co2.value = 0
        _voc.value = 0.0
        readingHistory.clear()
        _aiRecommendation.value = "Koneksi terputus."
    }

    fun fetchAiRecommendation() {
        viewModelScope.launch {
            _isRecommendationLoading.value = true
            
            // Collect features for current reading
            // Order: [aqi, temp, humidity, pm25, pm10, co2, voc, 0.0f]
            val currentReading = floatArrayOf(
                _aqi.value.toFloat(),
                _temperature.value.toFloat(),
                _humidity.value.toFloat(),
                _pm25.value.toFloat(),
                _pm10.value.toFloat(),
                _co2.value.toFloat(),
                _voc.value.toFloat(),
                0f
            )
            
            readingHistory.add(currentReading)
            if (readingHistory.size > 12) {
                readingHistory.removeAt(0)
            }
            
            val aiResult = tfLiteService?.getRecommendation(readingHistory)
            if (aiResult != null) {
                _aiRecommendation.value = aiResult.recommendation
                _lastAiStatus = aiResult.status
                _lastAiAnomaly = aiResult.isAnomaly
                checkAndSendAirQualityWarning(aiResult.isAnomaly)
            } else {
                _aiRecommendation.value = "Menunggu inisialisasi AI..."
            }
            _isRecommendationLoading.value = false
        }
    }

    fun saveSettings(settings: AppSettings, reconnect: Boolean = false) {
        viewModelScope.launch {
            repository.updateSettings(settings)
            
            // Manage background service & weekly report
            updateServiceState(settings.enableBackgroundMonitoring)
            updateWeeklyReportState(settings.enableWeeklyReport)
            
            // Only trigger a connection attempt when explicitly requested
            // (e.g., when the user presses Connect, not when toggling unrelated switches)
            if (reconnect) {
                if (settings.connectionMode == "direct") {
                    fetchDirectReading(settings.sensorIp)
                } else if (settings.connectionMode == "backend") {
                    fetchBackendReadings(settings.backendUrl)
                } else {
                    _connectionState.value = SensorConnectionState.Connected
                }
            }
        }
    }

    private fun updateWeeklyReportState(enable: Boolean) {
        val workManager = WorkManager.getInstance(getApplication())
        val workName = "AirKuWeeklyReportWork"
        if (enable) {
            val request = PeriodicWorkRequestBuilder<com.airkuapp.service.WeeklyReportWorker>(
                7, java.util.concurrent.TimeUnit.DAYS
            ).build()
            workManager.enqueueUniquePeriodicWork(
                workName,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        } else {
            workManager.cancelUniqueWork(workName)
        }
    }

    private fun updateServiceState(enable: Boolean) {
        val context = getApplication<Application>()
        val intent = android.content.Intent(context, com.airkuapp.service.AirQualityMonitorService::class.java)
        if (enable) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        } else {
            context.stopService(intent)
        }
    }

    fun addNewReadingToHistory(location: String) {
        // Only save if actually connected and data is real (non-zero)
        val isConnected = _connectionState.value == SensorConnectionState.Connected
        if (!isConnected || _aqi.value == 0) return

        val settings = appSettings.value
        viewModelScope.launch {
            val status = _lastAiStatus
            val log = AirQualityLog(
                timestamp = if (settings.enableSimulation) System.currentTimeMillis() else (lastSensorTimestamp ?: System.currentTimeMillis()),
                aqi = _aqi.value,
                temperature = _temperature.value,
                humidity = _humidity.value,
                pm25 = _pm25.value,
                pm10 = _pm10.value,
                co2 = _co2.value,
                voc = _voc.value,
                location = location,
                status = status
            )
            repository.insertLog(log)
        }
    }

    fun deleteLog(id: Int) {
        viewModelScope.launch {
            repository.deleteLog(id)
        }
    }
}
