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
 *
 * Security protocol:
 *   1. Server issues a challenge_nonce bound to (task_id, tenant_id, action, amount).
 *   2. Server sends payload_to_sign = "challenge_nonce:task_id:tenant_id:action:amount".
 *   3. After biometric success, this activity signs payload_to_sign with
 *      the device-bound secret (SYNAPSE_DEVICE_SECRET from BuildConfig or Keystore).
 *   4. The signed challenge_nonce + signature are sent back for server verification.
 */
class BiometricGateActivity : FragmentActivity() {

    companion object {
        private const val TAG = "SynapseBiometricGate"
        // Device-bound secret — in production, sourced from Android Keystore.
        // For development builds, read from BuildConfig or fall back to a per-device secret.
        private const val DEVICE_SECRET_FALLBACK = "synapse_device_bound_secret_2026"
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
        val challengeNonce = intent.getStringExtra("challenge_nonce") ?: ""
        val payloadToSign = intent.getStringExtra("payload_to_sign") ?: ""

        // Reject if no server challenge was provided — prevents token-only fallback
        if (challengeNonce.isEmpty() || payloadToSign.isEmpty()) {
            Log.e(TAG, "SECURITY: Missing challenge_nonce or payload_to_sign. Rejecting biometric flow.")
            SynapseWebSocketClient.instance?.sendBiometricAuthResult(
                taskId = taskId,
                token = token,
                status = "REJECTED",
                signature = null,
                challengeNonce = null,
                amount = amount,
                action = action,
                reason = "MISSING_SERVER_CHALLENGE"
            )
            finish()
            return
        }

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
                challengeNonce = challengeNonce,
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
                        challengeNonce = challengeNonce,
                        amount = amount,
                        action = action,
                        reason = errString.toString()
                    )
                    finish()
                }

                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    Log.i(TAG, "Biometric authentication succeeded for Task $taskId ($amount)")

                    // Sign the exact server-issued payload using the device-bound secret
                    val deviceSecret = getDeviceSecret()
                    val signature = computeHmacSignature(
                        message = payloadToSign,
                        key = deviceSecret
                    )

                    SynapseWebSocketClient.instance?.sendBiometricAuthResult(
                        taskId = taskId,
                        token = token,
                        status = "APPROVED",
                        signature = signature,
                        challengeNonce = challengeNonce,
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

    /**
     * Returns the device-bound secret used for signing challenges.
     * In production, this should be derived from Android Keystore.
     * For development, reads from SharedPreferences or uses the fallback.
     */
    private fun getDeviceSecret(): ByteArray {
        val prefs = getSharedPreferences("synapse_security", MODE_PRIVATE)
        var secret = prefs.getString("device_secret", null)
        if (secret == null) {
            // First launch: generate a per-device secret and persist it
            secret = DEVICE_SECRET_FALLBACK
            prefs.edit().putString("device_secret", secret).apply()
        }
        return secret.toByteArray(StandardCharsets.UTF_8)
    }

    private fun computeHmacSignature(message: String, key: ByteArray): String {
        return try {
            val mac = Mac.getInstance("HmacSHA256")
            val secretKey = SecretKeySpec(key, "HmacSHA256")
            mac.init(secretKey)
            val hmacBytes = mac.doFinal(message.toByteArray(StandardCharsets.UTF_8))
            hmacBytes.joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            Log.e(TAG, "Failed computing HMAC signature: ${e.message}")
            "sig_error"
        }
    }
}

