package com.synapse.ai.overlay

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import androidx.core.app.NotificationCompat
import com.synapse.ai.R

class FloatingCharacterOverlayService : Service() {

    companion object {
        private const val TAG = "FloatingOverlay"
        private const val CHANNEL_ID = "synapse_overlay_channel"
        private const val NOTIFICATION_ID = 1001

        var instance: FloatingCharacterOverlayService? = null
            private set
    }

    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private lateinit var layoutParams: WindowManager.LayoutParams

    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        startForeground(NOTIFICATION_ID, createNotification())
        setupOverlayView()
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        overlayView?.let { windowManager.removeView(it) }
    }

    private fun createNotification(): Notification {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Synapse Living Character",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Synapse AI Active")
            .setContentText("Your personal phone agent is observing and ready.")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
    }

    private fun setupOverlayView() {
        val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                    WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 40
            y = 300
        }

        // Programmatic overlay view container with drag handling
        val container = FrameLayout(this).apply {
            setPadding(16, 16, 16, 16)
        }

        // Character visual placeholder widget (in full app, renders Jetpack Compose or dynamic SVG canvas)
        val characterIcon = ImageView(this).apply {
            setImageResource(android.R.drawable.presence_online)
            val sizePx = (72 * resources.displayMetrics.density).toInt()
            layoutParams = FrameLayout.LayoutParams(sizePx, sizePx).apply {
                gravity = Gravity.CENTER
            }
        }
        container.addView(characterIcon)

        // Speech Bubble View
        val speechBubble = TextView(this).apply {
            text = "Synapse Ready"
            textSize = 11f
            setTextColor(0xFFFFFFFF.toInt())
            setBackgroundColor(0xCC0f131a.toInt())
            setPadding(12, 6, 12, 6)
            visibility = View.VISIBLE
        }
        container.addView(speechBubble)

        // Drag & Touch Listener
        container.setOnTouchListener { view, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = layoutParams.x
                    initialY = layoutParams.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    layoutParams.x = initialX + (event.rawX - initialTouchX).toInt()
                    layoutParams.y = initialY + (event.rawY - initialTouchY).toInt()
                    windowManager.updateViewLayout(container, layoutParams)
                    true
                }
                MotionEvent.ACTION_UP -> {
                    // Tap detection (distance moved < 15px)
                    val diffX = Math.abs(event.rawX - initialTouchX)
                    val diffY = Math.abs(event.rawY - initialTouchY)
                    if (diffX < 15 && diffY < 15) {
                        onCharacterTapped()
                    }
                    true
                }
                else -> false
            }
        }

        overlayView = container
        windowManager.addView(overlayView, layoutParams)
    }

    private fun onCharacterTapped() {
        Log.i(TAG, "Floating character tapped - toggling assistant voice input.")
        // Broadcasts intent or triggers quick voice listening
    }

    fun updateCharacterState(state: String, speech: String?) {
        overlayView?.post {
            val speechView = (overlayView as? FrameLayout)?.getChildAt(1) as? TextView
            if (!speech.isNullOrBlank()) {
                speechView?.text = speech
                speechView?.visibility = View.VISIBLE
            } else {
                speechView?.visibility = View.GONE
            }
        }
    }
}
