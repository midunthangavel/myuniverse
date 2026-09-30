package com.synapse.ai.network

import android.content.Context
import android.media.MediaPlayer
import android.util.Base64
import android.util.Log
import com.synapse.ai.accessibility.SynapseAccessibilityService
import com.synapse.ai.overlay.FloatingCharacterOverlayService
import okhttp3.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit

class SynapseWebSocketClient(
    private val context: Context,
    private val serverUrl: String = "ws://10.0.2.2:8000/ws/agent" // 10.0.2.2 is host loopback in Android Emulator
) {
    companion object {
        private const val TAG = "SynapseWS"
    }

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    var isConnected = false
        private set

    fun connect() {
        val request = Request.Builder().url(serverUrl).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "Connected to Synapse Cloud Backend at $serverUrl")
                isConnected = true
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val msg = JSONObject(text)
                    handleServerEvent(msg)
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing server message: ${e.message}")
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "WebSocket failure: ${t.message}. Reconnecting in 5s...")
                isConnected = false
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                isConnected = false
            }
        })
    }

    private fun handleServerEvent(msg: JSONObject) {
        val type = msg.optString("type")

        when (type) {
            "CHARACTER_STATE" -> {
                val state = msg.optString("state", "IDLE")
                val speech = msg.optString("speech", "")
                FloatingCharacterOverlayService.instance?.updateCharacterState(state, speech)

                val audioBase64 = msg.optString("audio_data_uri", "")
                if (audioBase64.isNotEmpty()) {
                    playAudioBase64(audioBase64)
                }
            }

            "LOG_STEP" -> {
                val step = msg.optString("step")
                val title = msg.optString("title")
                Log.i(TAG, "[$step] $title")
            }

            "HIGH_RISK_PROMPT" -> {
                // Triggers Biometric Authorization Gate
                val plan = msg.optJSONObject("plan")
                Log.w(TAG, "HIGH RISK PROMPT: ${plan?.optString("summary")}")
                // In full app: Launches BiometricPrompt
            }

            "ACTION_CONFIRMED" -> {
                val speech = msg.optString("speech", "Confirmed")
                FloatingCharacterOverlayService.instance?.updateCharacterState("SUCCESS", speech)
            }
        }
    }

    fun sendTask(prompt: String) {
        val accessibility = SynapseAccessibilityService.instance
        val screenNodes = accessibility?.dumpScreenHierarchy() ?: emptyList()

        val jsonNodes = JSONArray()
        screenNodes.forEach { jsonNodes.put(it.toJson()) }

        val screenContext = JSONObject().apply {
            put("app", "active_window")
            put("title", "Current Mobile View")
            put("visible_nodes", jsonNodes)
        }

        val payload = JSONObject().apply {
            put("type", "RUN_TASK")
            put("prompt", prompt)
            put("screen_context", screenContext)
            put("user_id", "user_default")
        }

        webSocket?.send(payload.toString())
    }

    private fun playAudioBase64(dataUri: String) {
        try {
            val base64 = dataUri.substringAfter("base64,")
            val decoded = Base64.decode(base64, Base64.DEFAULT)

            val tempFile = File.createTempFile("synapse_speech", ".mp3", context.cacheDir)
            FileOutputStream(tempFile).use { it.write(decoded) }

            MediaPlayer().apply {
                setDataSource(tempFile.absolutePath)
                prepare()
                start()
                setOnCompletionListener {
                    it.release()
                    tempFile.delete()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error playing audio: ${e.message}")
        }
    }

    fun disconnect() {
        webSocket?.close(1000, "App closed")
    }
}
