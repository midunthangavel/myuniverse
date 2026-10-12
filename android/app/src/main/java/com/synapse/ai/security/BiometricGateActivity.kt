package com.synapse.ai.security

import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.synapse.ai.network.SynapseWebSocketClient
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executor
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * High-Risk Biometric Authorization Gate for Synapse Agent.
 * Intercepts high-financial or sensitive actions and demands cryptographic
 * biometric hardware authentication (fingerprint/face) or device credential before commit.
 */
class BiometricGateActivity : FragmentActivity() {

    companion object {
        private const val TAG = "SynapseBiometricGate"
    }

    private lateinit var executor: Executor
    private lateinit var biometricPrompt: BiometricPrompt
    private lateinit var promptInfo: BiometricPrompt.PromptInfo

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val taskId = intent.getStringExtra("task_id") ?: "unknown_task"
        val token = intent.getStringExtra("token") ?: ""
        val amount = intent.getStringExtra("amount") ?: "$0.00"
        val action = intent.getStringExtra("action") ?: "Payment Execution"
        val scope = intent.getStringExtra("scope") ?: "FINANCIAL_PAYMENT"

        executor = ContextCompat.getMainExecutor(this)

        val biometricManager = BiometricManager.from(this)
        val canAuthenticate = biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL
        )

        if (canAuthenticate != BiometricManager.BIOMETRIC_SUCCESS) {
            Log.w(TAG, "Biometric authentication not supported or enrolled on device: code=$canAuthenticate")
            SynapseWebSocketClient.instance?.sendBiometricAuthResult(
                taskId = taskId,
                token = token,
                status = "REJECTED",
                signature = null,
                amount = amount,
                action = action,
                reason = "BIOMETRIC_UNAVAILABLE_CODE_$canAuthenticate"
            )
            finish()
            return
        }

        biometricPrompt = BiometricPrompt(
            this,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    Log.e(TAG, "Biometric authentication error ($errorCode): $errString")
                    SynapseWebSocketClient.instance?.sendBiometricAuthResult(
                        taskId = taskId,
                        token = token,
                        status = "REJECTED",
                        signature = null,
                        amount = amount,
                        action = action,
                        reason = errString.toString()
                    )
                    finish()
                }

                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    Log.i(TAG, "Biometric authentication succeeded for Task $taskId ($amount)")

                    val timestamp = System.currentTimeMillis() / 1000
                    val signature = computeHmacSignature(
                        message = "$taskId:$amount:$scope:$timestamp",
                        keyStr = token.ifEmpty { "synapse_gate_default_secret" }
                    )

                    SynapseWebSocketClient.instance?.sendBiometricAuthResult(
                        taskId = taskId,
                        token = token,
                        status = "APPROVED",
                        signature = signature,
                        amount = amount,
                        action = action,
                        reason = null
                    )
                    Toast.makeText(this@BiometricGateActivity, "Action Authorized", Toast.LENGTH_SHORT).show()
                    finish()
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    Log.w(TAG, "Biometric authentication attempt failed (unrecognized credential).")
                }
            }
        )

        promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Synapse Governance Gate")
            .setSubtitle("Authorize $amount for $action")
            .setDescription("Task ID: $taskId\nBiometric authorization is required to commit this action.")
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL
            )
            .build()

        biometricPrompt.authenticate(promptInfo)
    }

    private fun computeHmacSignature(message: String, keyStr: String): String {
        return try {
            val keyBytes = keyStr.toByteArray(StandardCharsets.UTF_8)
            val mac = Mac.getInstance("HmacSHA256")
            val secretKey = SecretKeySpec(keyBytes, "HmacSHA256")
            mac.init(secretKey)
            val hmacBytes = mac.doFinal(message.toByteArray(StandardCharsets.UTF_8))
            hmacBytes.joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            Log.e(TAG, "Failed computing HMAC signature: ${e.message}")
            "sig_error"
        }
    }
}
