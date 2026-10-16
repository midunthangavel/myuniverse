package com.synapse.ai.network

import android.content.Context
import android.content.Intent
import android.media.MediaPlayer
import android.util.Base64
import android.util.Log
import com.synapse.ai.accessibility.SynapseAccessibilityService
import com.synapse.ai.overlay.FloatingCharacterOverlayService
import com.synapse.ai.security.BiometricGateActivity
import okhttp3.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import android.os.Handler
import android.os.Looper

class SynapseWebSocketClient(
    private val context: Context,
    private val serverUrl: String = "ws://127.0.0.1:8000/ws/agent?token=dev_token_nexus_01"
) {
    companion object {
        private const val TAG = "SynapseWS"
        var instance: SynapseWebSocketClient? = null
            private set
    }

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    var isConnected = false
        private set

    init {
        instance = this
    }

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
                Log.w(TAG, "WebSocket failure: ${t.message}. Reconnecting in 5s...", t)
                isConnected = false
                Handler(Looper.getMainLooper()).postDelayed({
                    connect()
                }, 5000)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                isConnected = false
                Handler(Looper.getMainLooper()).postDelayed({
                    connect()
                }, 5000)
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

            "HIGH_RISK_PROMPT", "FINANCIAL_AUTH_REQUIRED" -> {
                val plan = msg.optJSONObject("plan")
                val taskId = msg.optString("task_id", plan?.optString("task_id", "unknown_task") ?: "unknown_task")
                val token = msg.optString("token", plan?.optString("token", "") ?: "")
                val amount = msg.optString("amount", plan?.optString("amount", "$0.00") ?: "$0.00")
                val action = msg.optString("action", plan?.optString("summary", "Payment Action") ?: "Payment Action")
                val scope = msg.optString("scope", "FINANCIAL_PAYMENT")
                val challengeNonce = msg.optString("challenge_nonce", plan?.optString("challenge_nonce", "") ?: "")
                val payloadToSign = msg.optString("payload_to_sign", plan?.optString("payload_to_sign", "") ?: "")

                Log.w(TAG, "HIGH RISK PROMPT received. Launching Native Biometric Gate for Task: $taskId ($amount)")

                val intent = Intent(context, BiometricGateActivity::class.java).apply {
                    putExtra("task_id", taskId)
                    putExtra("token", token)
                    putExtra("amount", amount)
                    putExtra("action", action)
                    putExtra("scope", scope)
                    putExtra("challenge_nonce", challengeNonce)
                    putExtra("payload_to_sign", payloadToSign)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            }

            "ACTION_CONFIRMED" -> {
                val speech = msg.optString("speech", "Confirmed")
                FloatingCharacterOverlayService.instance?.updateCharacterState("SUCCESS", speech)
            }

            "COMMAND" -> {
                handleCommand(msg)
            }
        }
    }

    private fun handleCommand(msg: JSONObject) {
        val taskId = msg.optString("task_id")
        val commandId = msg.optString("command_id")
        val sequence = msg.optInt("sequence")
        val action = msg.optJSONObject("action")

        if (action == null) {
            sendErrorResult(taskId, commandId, sequence, "MISSING_ACTION")
            return
        }

        val accessibility = SynapseAccessibilityService.instance
        if (accessibility == null) {
            sendErrorResult(taskId, commandId, sequence, "ACCESSIBILITY_SERVICE_NOT_RUNNING")
            return
        }

        val actionType = action.optString("type")
        val target = action.optJSONObject("target")
        val resourceId = target?.optString("resource_id")

        val handler = Handler(Looper.getMainLooper())

        when (actionType) {
            "OPEN_APP" -> {
                val pkg = action.optString("package")
                try {
                    var launchIntent = context.packageManager.getLaunchIntentForPackage(pkg)
                    if (launchIntent == null && pkg == "com.instagram.android") {
                        launchIntent = Intent(Intent.ACTION_VIEW, android.net.Uri.parse("instagram://direct")).apply {
                            setPackage(pkg)
                        }
                    }
                    if (launchIntent == null) {
                        launchIntent = Intent(Intent.ACTION_MAIN).apply {
                            addCategory(Intent.CATEGORY_LAUNCHER)
                            setPackage(pkg)
                        }
                    }
                    launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(launchIntent)
                    handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 2500)
                    return
                } catch (e: Exception) {
                    sendErrorResult(taskId, commandId, sequence, "LAUNCH_FAILED: ${e.message}")
                    return
                }
            }

            "TAP" -> {
                if (resourceId != null) {
                    // Resilient node lookup with dynamic scrolling and IME dismissal
                    accessibility.findNodeWithScroll(resourceId, maxScrolls = 2) { node ->
                        if (node != null) {
                            accessibility.performClick(node.bounds.centerX().toFloat(), node.bounds.centerY().toFloat()) { _ ->
                                handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1500)
                            }
                        } else {
                            // Check if soft keyboard is obscuring element
                            accessibility.dismissKeyboard()
                            handler.postDelayed({
                                val retryNode = accessibility.findNodeById(resourceId)
                                if (retryNode != null) {
                                    accessibility.performClick(retryNode.bounds.centerX().toFloat(), retryNode.bounds.centerY().toFloat()) { _ ->
                                        handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1500)
                                    }
                                } else {
                                    sendErrorResult(taskId, commandId, sequence, "TARGET_NOT_FOUND_AFTER_SCROLL_AND_KEYBOARD_DISMISS: $resourceId")
                                }
                            }, 300)
                        }
                    }
                    return
                } else if (action.has("x") && action.has("y")) {
                    val x = action.optDouble("x").toFloat()
                    val y = action.optDouble("y").toFloat()
                    accessibility.performClick(x, y) { _ ->
                        handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1500)
                    }
                    return
                } else {
                    sendErrorResult(taskId, commandId, sequence, "TAP_MISSING_TARGET_OR_COORDINATES")
                    return
                }
            }

            "TYPE" -> {
                val text = action.optString("value")
                val targetNode = if (resourceId != null) accessibility.findNodeById(resourceId) else accessibility.findFirstEditableNode()
                if (targetNode != null) {
                    accessibility.performClick(targetNode.bounds.centerX().toFloat(), targetNode.bounds.centerY().toFloat()) { _ ->
                        handler.postDelayed({
                            accessibility.performSetText(text)
                            handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1000)
                        }, 500)
                    }
                    return
                } else {
                    // Try to dismiss keyboard and find editable node
                    accessibility.dismissKeyboard()
                    handler.postDelayed({
                        val fallbackEditable = accessibility.findFirstEditableNode()
                        if (fallbackEditable != null) {
                            accessibility.performClick(fallbackEditable.bounds.centerX().toFloat(), fallbackEditable.bounds.centerY().toFloat()) { _ ->
                                handler.postDelayed({
                                    accessibility.performSetText(text)
                                    handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1000)
                                }, 500)
                            }
                        } else {
                            sendErrorResult(taskId, commandId, sequence, "NO_EDITABLE_TARGET_FOUND_ON_SCREEN")
                        }
                    }, 300)
                    return
                }
            }

            "SWIPE" -> {
                val dir = action.optString("direction", "UP")
                if (dir == "UP") {
                    accessibility.performSwipe(500f, 1500f, 500f, 500f) { _ ->
                        handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1500)
                    }
                } else {
                    accessibility.performSwipe(500f, 500f, 500f, 1500f) { _ ->
                        handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility) }, 1500)
                    }
                }
                return
            }

            "GLOBAL_ACTION" -> {
                val name = action.optString("name")
                val success = when (name) {
                    "BACK" -> accessibility.performBack()
                    "HOME" -> accessibility.performHome()
                    "RECENTS" -> accessibility.performRecents()
                    else -> false
                }
                handler.postDelayed({ sendCommandResult(taskId, commandId, sequence, if (success) "DISPATCHED" else "FAILED", accessibility) }, 1500)
                return
            }

            "OBSERVE_ONLY" -> {
                sendCommandResult(taskId, commandId, sequence, "DISPATCHED", accessibility)
                return
            }

            else -> {
                sendErrorResult(taskId, commandId, sequence, "UNKNOWN_ACTION_TYPE: $actionType")
                return
            }
        }
    }

    private fun sendCommandResult(taskId: String, commandId: String, sequence: Int, status: String, accessibility: SynapseAccessibilityService) {
        val screenNodes = accessibility.dumpScreenHierarchy(forceRefresh = true)
        val jsonNodes = JSONArray()
        val sb = StringBuilder()

        val fgPackage = screenNodes.firstOrNull()?.packageName ?: "unknown"
        sb.append(fgPackage).append("|")

        screenNodes.forEach {
            jsonNodes.put(it.toJson())
            sb.append(it.id).append(":")
                .append(it.text).append(":")
                .append(it.contentDescription).append(":")
                .append(it.className).append(":")
                .append(it.isClickable).append(":")
                .append(it.bounds.toShortString()).append(";")
        }

        val bytes = MessageDigest.getInstance("SHA-256").digest(sb.toString().toByteArray())
        val fingerprint = bytes.joinToString("") { "%02x".format(it) }

        val payload = JSONObject().apply {
            put("type", "COMMAND_RESULT")
            put("task_id", taskId)
            put("command_id", commandId)
            put("sequence", sequence)
            put("status", status)
            put("execution_status", status)
            put("screen_fingerprint", fingerprint)
            put("observation", JSONObject().apply {
                put("foreground_package", fgPackage)
                put("visible_nodes", jsonNodes)
            })
        }
        webSocket?.send(payload.toString())
    }

    private fun sendErrorResult(taskId: String, commandId: String, sequence: Int, reason: String) {
        val payload = JSONObject().apply {
            put("type", "COMMAND_RESULT")
            put("task_id", taskId)
            put("command_id", commandId)
            put("sequence", sequence)
            put("status", "FAILED")
            put("execution_status", "FAILED")
            put("reason", reason)
        }
        webSocket?.send(payload.toString())
    }

    fun sendBiometricAuthResult(
        taskId: String,
        token: String?,
        status: String,
        signature: String? = null,
        challengeNonce: String? = null,
        amount: String? = null,
        action: String? = null,
        reason: String? = null
    ) {
        val payload = JSONObject().apply {
            put("type", "BIOMETRIC_AUTH_RESULT")
            put("task_id", taskId)
            put("token", token ?: "")
            put("status", status)
            put("signature", signature ?: "")
            put("challenge_nonce", challengeNonce ?: "")
            put("amount", amount ?: "")
            put("action", action ?: "")
            put("reason", reason ?: "")
        }
        webSocket?.send(payload.toString())
    }

    fun sendTask(prompt: String) {
        val screenContext = JSONObject().apply {
            put("app", "test_app")
            put("title", "Test Title")
            put("visible_nodes", JSONArray())
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
