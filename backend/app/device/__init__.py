"""
Device Abstraction Layer for Synapse AI Agent.
Exposes BaseDeviceController, AndroidADBController, IOSWDAController, SimulatorController,
DeviceControllerFactory, and the Android Agent Runtime:
- AndroidStateEngine (Multimodal Perception)
- AndroidGroundingEngine (Semantic Intent to Coordinate Resolution)
- AndroidActionEngine (Native Intents, Actions & Gestures)
- TaskVerificationEngine (Temporal Diff & Recovery)
- MultiAppOrchestrator (Cross-App Workflow Execution)
"""

from .base_controller import BaseDeviceController, ActionResult
from .android_controller import AndroidADBController
from .ios_controller import IOSWDAController
from .sim_controller import SimulatorController
from .controller_factory import device_factory, DeviceControllerFactory
from .ui_parser import UIAutomatorParser

from .state_engine import android_state_engine, AndroidStateEngine, AndroidScreenState, AndroidUIElement
from .grounding_engine import android_grounding_engine, AndroidGroundingEngine, GroundingResult
from .action_engine import android_action_engine, AndroidActionEngine, ActionExecutionResult
from .verification_engine import task_verification_engine, TaskVerificationEngine, ExpectedOutcome, VerificationResult
from .multi_app_runner import multi_app_orchestrator, MultiAppOrchestrator

__all__ = [
    "BaseDeviceController",
    "ActionResult",
    "AndroidADBController",
    "IOSWDAController",
    "SimulatorController",
    "DeviceControllerFactory",
    "device_factory",
    "UIAutomatorParser",
    "android_state_engine",
    "AndroidStateEngine",
    "AndroidScreenState",
    "AndroidUIElement",
    "android_grounding_engine",
    "AndroidGroundingEngine",
    "GroundingResult",
    "android_action_engine",
    "AndroidActionEngine",
    "ActionExecutionResult",
    "task_verification_engine",
    "TaskVerificationEngine",
    "ExpectedOutcome",
    "VerificationResult",
    "multi_app_orchestrator",
    "MultiAppOrchestrator"
]
