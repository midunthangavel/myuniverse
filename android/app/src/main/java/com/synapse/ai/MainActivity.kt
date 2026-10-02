package com.synapse.ai

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import com.synapse.ai.accessibility.SynapseAccessibilityService
import com.synapse.ai.overlay.FloatingCharacterOverlayService
import com.synapse.ai.capture.ScreenCaptureService

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Intentions to start services would go here
    }
}
