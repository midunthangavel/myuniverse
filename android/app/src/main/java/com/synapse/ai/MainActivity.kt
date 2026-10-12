package com.synapse.ai

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.accessibility.AccessibilityManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.synapse.ai.accessibility.SynapseAccessibilityService
import com.synapse.ai.network.SynapseWebSocketClient
import com.synapse.ai.overlay.FloatingCharacterOverlayService

class MainActivity : ComponentActivity() {

    companion object {
        var wsClient: SynapseWebSocketClient? = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Automatically connect to backend via adb reverse reverse-port
        if (wsClient == null || wsClient?.isConnected == false) {
            val token = getSharedPreferences("synapse_prefs", Context.MODE_PRIVATE)
                .getString("device_token", "dev_token_nexus_01") ?: "dev_token_nexus_01"
            wsClient = SynapseWebSocketClient(this, "ws://127.0.0.1:8000/ws/agent?token=$token")
            wsClient?.connect()
        }
        setContent {
            SynapseDashboardScreen()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SynapseDashboardScreen() {
    val context = LocalContext.current
    var serverHost by remember { mutableStateOf("localhost") } // 'localhost' works with adb reverse
    var isOverlayGranted by remember { mutableStateOf(checkOverlayPermission(context)) }
    var isAccessibilityGranted by remember { mutableStateOf(checkAccessibilityPermission(context)) }
    var isConnected by remember { mutableStateOf(MainActivity.wsClient?.isConnected ?: false) }
    var isServiceRunning by remember { mutableStateOf(FloatingCharacterOverlayService.instance != null) }

    // Recheck permissions on resume / trigger
    LaunchedEffect(Unit) {
        while (true) {
            isOverlayGranted = checkOverlayPermission(context)
            isAccessibilityGranted = checkAccessibilityPermission(context)
            isServiceRunning = FloatingCharacterOverlayService.instance != null
            isConnected = MainActivity.wsClient?.isConnected ?: false
            kotlinx.coroutines.delay(1000)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(12.dp)
                                .clip(CircleShape)
                                .background(if (isConnected) Color(0xFF10B981) else Color(0xFFEF4444))
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text("Synapse AI Assistant", fontWeight = FontWeight.Bold)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0F172A),
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = Color(0xFF090D16)
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(20.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Hero card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        "Autonomous Phone Agent",
                        color = Color(0xFF38BDF8),
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        "Synapse controls apps, reads UI elements, and automates tasks directly on your device via WebSocket commands.",
                        color = Color(0xFF94A3B8),
                        fontSize = 13.sp,
                        lineHeight = 18.sp
                    )
                }
            }

            // Permissions Section
            Text(
                "REQUIRED PERMISSIONS",
                color = Color(0xFF64748B),
                fontWeight = FontWeight.Bold,
                fontSize = 12.sp
            )

            // Permission Item 1: Overlay
            PermissionCard(
                title = "Display Over Other Apps",
                description = "Needed for the floating AI assistant character.",
                isGranted = isOverlayGranted,
                actionLabel = if (isOverlayGranted) "Granted" else "Enable",
                onClick = {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        val intent = Intent(
                            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            Uri.parse("package:${context.packageName}")
                        )
                        context.startActivity(intent)
                    }
                }
            )

            // Permission Item 2: Accessibility
            PermissionCard(
                title = "Accessibility Service",
                description = "Allows Synapse to tap, scroll, and read UI hierarchy.",
                isGranted = isAccessibilityGranted,
                actionLabel = if (isAccessibilityGranted) "Active" else "Enable in Settings",
                onClick = {
                    val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                    context.startActivity(intent)
                }
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Backend Server Configuration
            Text(
                "BACKEND SERVER (WEBSOCKET)",
                color = Color(0xFF64748B),
                fontWeight = FontWeight.Bold,
                fontSize = 12.sp
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B)),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedTextField(
                        value = serverHost,
                        onValueChange = { serverHost = it },
                        label = { Text("Server Host / IP", color = Color(0xFF94A3B8)) },
                        placeholder = { Text("e.g. 192.168.1.5 or 10.0.2.2") },
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color(0xFF38BDF8),
                            unfocusedBorderColor = Color(0xFF334155)
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Text(
                        "• Use '10.0.2.2' if running in Android Emulator\n• Use your PC's Wi-Fi IP (e.g. 192.168.x.x) or 'localhost' if using 'adb reverse tcp:8000 tcp:8000'",
                        color = Color(0xFF64748B),
                        fontSize = 12.sp
                    )

                    Button(
                        onClick = {
                            val wsUrl = "ws://$serverHost:8000/ws/agent?token=prod_token_xyz_2026"
                            MainActivity.wsClient = SynapseWebSocketClient(context, wsUrl)
                            MainActivity.wsClient?.connect()
                            Toast.makeText(context, "Connecting to $wsUrl...", Toast.LENGTH_SHORT).show()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(if (isConnected) "Connected (Reconnect)" else "Connect to Backend")
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Overlay Floating Character Trigger
            Button(
                onClick = {
                    if (!isOverlayGranted) {
                        Toast.makeText(context, "Please grant Overlay permission first!", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    if (isServiceRunning) {
                        val stopIntent = Intent(context, FloatingCharacterOverlayService::class.java)
                        context.stopService(stopIntent)
                        isServiceRunning = false
                    } else {
                        val startIntent = Intent(context, FloatingCharacterOverlayService::class.java)
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            context.startForegroundService(startIntent)
                        } else {
                            context.startService(startIntent)
                        }
                        isServiceRunning = true
                    }
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isServiceRunning) Color(0xFFDC2626) else Color(0xFF10B981)
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Icon(if (isServiceRunning) Icons.Default.Close else Icons.Default.PlayArrow, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    if (isServiceRunning) "Stop Floating Overlay" else "Launch Floating AI Character",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
fun PermissionCard(
    title: String,
    description: String,
    isGranted: Boolean,
    actionLabel: String,
    onClick: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B)),
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f).padding(end = 12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(if (isGranted) Color(0xFF10B981) else Color(0xFFF59E0B))
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(title, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(description, color = Color(0xFF94A3B8), fontSize = 12.sp)
            }

            Button(
                onClick = onClick,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isGranted) Color(0xFF0F766E) else Color(0xFF2563EB)
                ),
                shape = RoundedCornerShape(8.dp),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
            ) {
                Text(actionLabel, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

fun checkOverlayPermission(context: Context): Boolean {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
        Settings.canDrawOverlays(context)
    } else {
        true
    }
}

fun checkAccessibilityPermission(context: Context): Boolean {
    val am = context.getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
    val enabledServices = Settings.Secure.getString(
        context.contentResolver,
        Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
    ) ?: return false

    return enabledServices.contains(context.packageName)
}
