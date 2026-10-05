package com.synapse.ai.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

data class ScreenNode(
    val id: String?,
    val text: String?,
    val contentDescription: String?,
    val className: String?,
    val bounds: Rect,
    val isClickable: Boolean,
    val isScrollable: Boolean,
    val isEditable: Boolean,
    val packageName: String?
) {
    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("id", id ?: "")
            put("text", text ?: "")
            put("desc", contentDescription ?: "")
            put("className", className ?: "")
            put("clickable", isClickable)
            put("scrollable", isScrollable)
            put("editable", isEditable)
            put("bounds", JSONArray(listOf(bounds.left, bounds.top, bounds.right, bounds.bottom)))
            put("center", JSONArray(listOf(bounds.centerX(), bounds.centerY())))
            put("package", packageName ?: "")
        }
    }
}

class SynapseAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "SynapseAccessibility"
        var instance: SynapseAccessibilityService? = null
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "Synapse Accessibility Service Connected & Active.")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        Log.i(TAG, "Synapse Accessibility Service Destroyed.")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Monitors window changes or active app switches
    }

    override fun onInterrupt() {
        Log.w(TAG, "Accessibility Service Interrupted.")
    }

    /**
     * Dumps the entire active window's AccessibilityNodeInfo tree.
     * Serializes interactive buttons, text fields, and list views.
     */
    fun dumpScreenHierarchy(): List<ScreenNode> {
        val root = rootInActiveWindow ?: return emptyList()
        val nodes = mutableListOf<ScreenNode>()
        traverseNode(root, nodes)
        return nodes
    }

    private fun traverseNode(node: AccessibilityNodeInfo?, list: MutableList<ScreenNode>) {
        if (node == null) return

        val bounds = Rect()
        node.getBoundsInScreen(bounds)

        // Only include nodes with visible dimensions
        if (bounds.width() > 0 && bounds.height() > 0) {
            val hasText = !node.text.isNullOrBlank() || !node.contentDescription.isNullOrBlank()
            val isInteractive = node.isClickable || node.isScrollable || node.isEditable

            if (hasText || isInteractive) {
                list.add(
                    ScreenNode(
                        id = node.viewIdResourceName,
                        text = node.text?.toString(),
                        contentDescription = node.contentDescription?.toString(),
                        className = node.className?.toString(),
                        bounds = bounds,
                        isClickable = node.isClickable,
                        isScrollable = node.isScrollable,
                        isEditable = node.isEditable,
                        packageName = node.packageName?.toString()
                    )
                )
            }
        }

        for (i in 0 until node.childCount) {
            traverseNode(node.getChild(i), list)
        }
    }

    fun findNodeById(target: String): ScreenNode? {
        val nodes = dumpScreenHierarchy()
        // 1. Exact or suffix id match (e.g. "direct_tab" matches "com.instagram.android:id/direct_tab")
        val byId = nodes.find {
            it.id != null && (it.id == target || it.id.endsWith("/$target") || it.id.contains(target, ignoreCase = true))
        }
        if (byId != null) return byId

        // 2. Exact text or content description
        val byExactText = nodes.find {
            it.text?.equals(target, ignoreCase = true) == true ||
            it.contentDescription?.equals(target, ignoreCase = true) == true
        }
        if (byExactText != null) return byExactText

        // 3. Substring match
        val byContains = nodes.find {
            it.text?.contains(target, ignoreCase = true) == true ||
            it.contentDescription?.contains(target, ignoreCase = true) == true
        }
        return byContains
    }

    /**
     * Programmatic Touch Tap Injection via Android Accessibility GestureDescription.
     * Dispatches physical tap without requiring root or developer options.
     */
    fun performClick(x: Float, y: Float, onComplete: ((Boolean) -> Unit)? = null) {
        val path = Path().apply {
            moveTo(x, y)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, 50)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                Log.d(TAG, "Gesture completed successfully at ($x, $y)")
                onComplete?.invoke(true)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                Log.e(TAG, "Gesture cancelled at ($x, $y)")
                onComplete?.invoke(false)
            }
        }, null)
    }

    /**
     * Programmatic Swipe/Scroll Gesture Injection.
     */
    fun performSwipe(startX: Float, startY: Float, endX: Float, endY: Float, durationMs: Long = 300, onComplete: ((Boolean) -> Unit)? = null) {
        val path = Path().apply {
            moveTo(startX, startY)
            lineTo(endX, endY)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                Log.d(TAG, "Swipe completed ($startX, $startY) -> ($endX, $endY)")
                onComplete?.invoke(true)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                Log.e(TAG, "Swipe cancelled")
                onComplete?.invoke(false)
            }
        }, null)
    }

    /**
     * Programmatic Text Input into Active or Focused EditText.
     */
    fun performSetText(text: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (focused != null && focused.isEditable) {
            val args = Bundle().apply {
                putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
            }
            return focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
        }

        fun findEditable(node: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
            if (node == null) return null
            if (node.isEditable) return node
            for (i in 0 until node.childCount) {
                val found = findEditable(node.getChild(i))
                if (found != null) return found
            }
            return null
        }
        val editable = findEditable(root)
        if (editable != null) {
            val args = Bundle().apply {
                putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
            }
            return editable.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
        }
        return false
    }

    fun performBack(): Boolean = performGlobalAction(GLOBAL_ACTION_BACK)
    fun performHome(): Boolean = performGlobalAction(GLOBAL_ACTION_HOME)
    fun performRecents(): Boolean = performGlobalAction(GLOBAL_ACTION_RECENTS)
}
