"""
Agent Intelligence Orchestrator (OODA / ReAct Loop)
Upgraded with:
1. Laya System 1 Fast Non-Autoregressive Decision Engine (<15ms choice, score, noul).
2. OpenViking Virtual Context Filesystem (viking://) with L0/L1/L2 progressive loading (~80% token savings).
3. Scrapling Stealth & Adaptive Web Intelligence Engine for live research.
4. QwenPaw Mobile Agent OS Loop with 3-Layer ReMe Memory & Composable ALLOW/ASK/DENY Governance.
5. Cloud Screen Perception (PaddleOCR + OmniParser + UGround) & Post-Action Verification.
6. Continuous Personalization Flywheel & Edge-TTS Neural Voice.
"""

import asyncio
import time
from typing import Dict, Any, AsyncGenerator, Optional
from .models import TaskRequest
from .memory import MemoryStore
from .vector_memory import VectorMemoryStore
from .vision import CloudScreenPerceptionEngine
from .learner import PersonalizationFlywheel
from .guardrails import GuardrailsEngine
from .tools import ToolRegistry
from .tool_registry import tool_registry, execute_tool
from .local_llm import LocalLLMClient
from .llm_factory import llm_factory
from .prompt_manager import prompt_manager, render_prompt
from .tts import NeuralTTS

# Wave 1 & Wave 2 Integrations
from .fast_classifier import LayaSystem1Classifier
from .context_fs import OpenVikingContextFS
from .scraper import WebIntelligenceEngine
from .paw_loop import ReMeMemory, QwenPawMobileLoop
from .reflector import action_reflector, trajectory_reflector
from .progressor import task_progressor
from .explorer import app_explorer
from .app_memory import app_specific_memory
from .financial_gate import financial_gate

class AgentOrchestrator:
    def __init__(
        self,
        memory_store: MemoryStore,
        vector_memory: Optional[VectorMemoryStore] = None,
        vision_engine: Optional[CloudScreenPerceptionEngine] = None,
        flywheel: Optional[PersonalizationFlywheel] = None
    ):
        self.memory = memory_store
        self.vector_memory = vector_memory or VectorMemoryStore()
        self.vision = vision_engine or CloudScreenPerceptionEngine()
        self.flywheel = flywheel or PersonalizationFlywheel(self.memory, self.vector_memory)
        self.guardrails = GuardrailsEngine()
        self.tools = ToolRegistry()
        self.local_llm = LocalLLMClient()
        self.tts = NeuralTTS()

        # Target Repo Integrations (Wave 1 & Wave 2)
        self.system1 = LayaSystem1Classifier()
        self.viking_fs = OpenVikingContextFS()
        self.scraper = WebIntelligenceEngine()
        self.reme = ReMeMemory()
        self.paw_loop = QwenPawMobileLoop(self.reme)
        self.reflector = action_reflector
        self.trajectory_reflector = trajectory_reflector
        self.progressor = task_progressor
        self.explorer = app_explorer
        self.app_memory = app_specific_memory
        self.financial_gate = financial_gate

    async def process_task_stream(self, request: TaskRequest) -> AsyncGenerator[Dict[str, Any], None]:
        user_prompt = request.prompt
        user_id = request.user_id
        active_app = request.screen_context.app if request.screen_context else "home"
        screen_title = request.screen_context.title if request.screen_context else "Active Screen"

        # Record in QwenPaw ReMe Layer 2 (Verbatim Episodic Turn)
        self.reme.record_turn("user", user_prompt, {"active_app": active_app, "title": screen_title})
        self.reme.reset_working_memory(user_prompt, request.screen_context.dict() if request.screen_context else {})

        # ==============================================================
        # STEP 1: LAYA SYSTEM 1 FAST CLASSIFICATION (<15ms single forward pass)
        # ==============================================================
        sys1_result = self.system1.classify_system1(user_prompt, active_app)

        # Immediate Character Micro-Reaction
        yield {
            "type": "CHARACTER_STATE",
            "state": sys1_result["suggested_character_state"],
            "speech": f'Got it! Evaluating "{user_prompt}"...'
        }

        # Check Laya 'noul' security gate
        if not sys1_result["noul"]["is_safe"]:
            yield {
                "type": "LOG_STEP",
                "step": "GOVERNANCE",
                "title": "Laya 'Noul' Gate: Security Violation Detected",
                "description": f"Blocked execution. Reason: {sys1_result['noul']['hazard_reason']}",
                "payload": sys1_result
            }
            yield {
                "type": "CHARACTER_STATE",
                "state": "ERROR",
                "speech": "I cannot proceed with this request as it violates device security guardrails."
            }
            return

        yield {
            "type": "LOG_STEP",
            "step": "SYSTEM1",
            "title": f"Laya System 1 Triage ({sys1_result['choice']} • {sys1_result['latency_ms']}ms)",
            "description": f"Non-autoregressive fast classification completed in {sys1_result['latency_ms']}ms. Calibrated confidence: {sys1_result['score']}. Safety Gate: PASSED.",
            "payload": {
                "engine": sys1_result["engine"],
                "choice": sys1_result["choice"],
                "confidence_score": sys1_result["score"],
                "noul_safety": sys1_result["noul"],
                "governance_mode": sys1_result["governance_action"],
                "latency_ms": sys1_result["latency_ms"]
            }
        }
        await asyncio.sleep(0.3)

        # ==============================================================
        # STEP 2: OPENVIKING VIRTUAL CONTEXT FILESYSTEM (viking:// L0/L1 Tiered Loading)
        # ==============================================================
        viking_loaded_nodes = []
        total_tokens_loaded = 0
        for uri in sys1_result["viking_preload"]:
            res = self.viking_fs.read(uri, tier="L1", tenant_id=user_id)
            if res.get("success"):
                viking_loaded_nodes.append(res)
                total_tokens_loaded += res.get("estimated_tokens", 0)

        # If empty, load default user profile
        if not viking_loaded_nodes:
            profile_res = self.viking_fs.read("viking://user/profile.md", tier="L1", tenant_id=user_id)
            viking_loaded_nodes.append(profile_res)
            total_tokens_loaded += profile_res.get("estimated_tokens", 0)

        yield {
            "type": "LOG_STEP",
            "step": "VIKING_FS",
            "title": f"OpenViking Progressive Context Loaded ({len(viking_loaded_nodes)} nodes, ~{total_tokens_loaded} tokens)",
            "description": "Utilized viking:// hierarchical filesystem protocol with L1 Overview tier (saving ~80% token overhead compared to flat dumps).",
            "payload": {
                "protocol": "viking://",
                "loaded_nodes": [
                    {"uri": n["uri"], "tier": n["tier"], "tokens": n["estimated_tokens"]}
                    for n in viking_loaded_nodes
                ],
                "sample_content": viking_loaded_nodes[0]["content"] if viking_loaded_nodes else ""
            }
        }
        await asyncio.sleep(0.3)

        # ==============================================================
        # STEP 3: SCRAPLING WEB INTELLIGENCE (If live research or prices/reviews needed)
        # ==============================================================
        web_intel_result = None
        needs_web = (
            sys1_result["choice"] in ["WEB_RESEARCH", "CINEMA_BOOKING", "FOOD_ORDERING"] or
            any(w in user_prompt.lower() for w in ["search", "check", "price", "reviews", "schedule", "tonight", "best"])
        )

        if needs_web:
            yield {
                "type": "CHARACTER_STATE",
                "state": "SEARCHING",
                "speech": "Consulting live web sources and checking schedules via stealth scraper..."
            }
            web_intel_result = await self.scraper.live_research(user_prompt)

            yield {
                "type": "LOG_STEP",
                "step": "SCRAPLING",
                "title": f"Scrapling Web Intelligence ({web_intel_result['total_results']} Sources Distilled)",
                "description": "Stealth mobile headers and adaptive DOM extractors retrieved live verified web facts.",
                "payload": web_intel_result
            }
            await asyncio.sleep(0.3)

        # ==============================================================
        # STEP 4: CLOUD SCREEN PERCEPTION (PaddleOCR + OmniParser Schema)
        # ==============================================================
        active_screen_nodes = [n.dict() for n in request.screen_context.visible_nodes] if request.screen_context else []
        parsed_screen = self.vision.parse_screen(
            accessibility_nodes=active_screen_nodes,
            active_app=active_app,
            screen_title=screen_title
        )

        yield {
            "type": "LOG_STEP",
            "step": "VISION",
            "title": f"Cloud Screen Perception ({parsed_screen['total_detected_elements']} UI Nodes Parsed)",
            "description": "Cloud perception pipeline (PaddleOCR + OmniParser) parsed UI regions, interactive buttons, and text blocks.",
            "payload": {
                "active_window": screen_title,
                "app": active_app,
                "clickable_regions": parsed_screen["clickable_count"],
                "ocr_blocks_count": len(parsed_screen["ocr_blocks"])
            }
        }
        await asyncio.sleep(0.3)

        # ==============================================================
        # STEP 5: DENSE VECTOR MEMORY & LOCAL LLM PLAN FORMULATION
        # ==============================================================
        semantic_matches = self.vector_memory.semantic_search(user_prompt, user_id=user_id, n_results=3)
        if not semantic_matches:
            raw_sqlite = self.memory.retrieve_context(user_id, "general", user_prompt)
            semantic_matches = [{"text": m["text"], "type": m["type"]} for m in raw_sqlite]

        # App-Specific RAG Memory Recall (Module 2.3)
        app_rag_shortcuts = self.app_memory.retrieve_similar_task(active_app, user_prompt, tenant_id=user_id)
        if app_rag_shortcuts:
            for s in app_rag_shortcuts:
                semantic_matches.append({"text": f"Known App Trajectory: {s.get('text', '')}", "type": "APP_SHORTCUT"})

        screen_ctx = request.screen_context.dict() if request.screen_context else {}
        plan = await self.local_llm.plan_task(user_prompt, semantic_matches, screen_ctx)

        # UGround Visual Coordinate Grounding
        grounding_result = self.vision.ground_instruction(user_prompt, parsed_screen)
        plan["visual_grounding"] = grounding_result

        # ==============================================================
        # STEP 6: QWENPAW COMPOSABLE GOVERNANCE & FINANCIAL GATE (ALLOW / ASK / DENY)
        # ==============================================================
        first_action = plan.get("steps", [{}])[0] if plan.get("steps") else {"action": "NAVIGATE"}
        governance_eval = self.paw_loop.evaluate_governance(plan.get("intent", "task"), {
            "action": first_action.get("action", "NAVIGATE"),
            "amount": plan.get("cost", "$0.00"),
            "summary": plan.get("summary", "Requested operation")
        })

        risk_tier = "high" if governance_eval["decision"] == "ASK" else "low"
        plan["risk_tier"] = risk_tier
        plan["governance"] = governance_eval

        task_id = f"task_{int(time.time() * 1000)}"
        plan["task_id"] = task_id

        # Cryptographic Financial Gate evaluation (Module 2.4)
        if governance_eval["decision"] == "ASK":
            gate_eval = self.financial_gate.evaluate_transaction(
                task_id=task_id,
                action=plan.get("intent", "task"),
                amount=plan.get("cost", "$0.00"),
                user_id=user_id
            )
            plan["financial_token"] = gate_eval["token"]
            plan["token_expires_in"] = gate_eval["expires_in_seconds"]

        yield {
            "type": "LOG_STEP",
            "step": "PLAN",
            "title": f"Local LLM Plan Formulated ({len(plan.get('steps', []))} Actions)",
            "description": f"QwenPaw Governance: [{governance_eval['decision']}]. Policy: {governance_eval['reason']}",
            "payload": {
                "plan": plan,
                "governance_decision": governance_eval,
                "visual_grounding": grounding_result
            }
        }
        await asyncio.sleep(0.3)

        # ==============================================================
        # STEP 7: HANDLE EXECUTION OR HIGH-RISK HUMAN-IN-THE-LOOP PROMPT
        # ==============================================================
        if governance_eval["decision"] == "ASK":
            speech_prompt = f"I've tailored the best option based on your habits. Shall I authorize the {plan['summary']}?"
            audio_uri = None
            try:
                audio_uri = await self.tts.generate_audio_base64(speech_prompt)
            except Exception as e:
                print(f"TTS error: {e}")

            yield {
                "type": "CHARACTER_STATE",
                "state": "WAITING_CONFIRM",
                "speech": speech_prompt,
                "audio_data_uri": audio_uri
            }
            yield {
                "type": "HIGH_RISK_PROMPT",
                "plan": plan,
                "audio_data_uri": audio_uri,
                "governance_mode": "ASK",
                "financial_token": plan.get("financial_token")
            }
        else:
            # Autonomous execution under ALLOW mode
            yield {
                "type": "CHARACTER_STATE",
                "state": "WORKING",
                "speech": "Executing grounded phone actions..."
            }
            await asyncio.sleep(0.3)

            # Module 2.1: Dynamic Closed-Loop Execution
            max_steps = 10
            executed_trajectory = []
            
            from .device.physical_phone_runtime import PhysicalPhoneRuntime
            physical_runtime = PhysicalPhoneRuntime(tenant_id=user_id)
            
            steps_list = plan.get("steps", [])
            task_success = True

            for step_idx, step in enumerate(steps_list):
                if step_idx >= max_steps:
                    break

                action_name = step.get("action", "ACT").upper()
                target = step.get("target", "")

                if action_name in ["DONE", "EXPLAIN_RESULT"]:
                    break

                # Execute using WSS PhysicalPhoneRuntime
                expected_outcome = {
                    "foreground_package": step.get("expected_package", ""),
                    "element_present": step.get("expected_element", "")
                }
                
                if action_name == "TAP":
                    exec_result = await physical_runtime.tap(resource_id=target, expected=expected_outcome)
                elif action_name in ["TYPE", "INPUT_TEXT"]:
                    exec_result = await physical_runtime.type(resource_id=target, text=step.get("text", step.get("value", "")), expected=expected_outcome)
                elif action_name == "SWIPE":
                    exec_result = await physical_runtime.swipe(direction="UP", expected=expected_outcome)
                elif action_name in ["GLOBAL_ACTION", "NAVIGATE", "PRESS_BACK", "PRESS_HOME"]:
                    exec_result = await physical_runtime.global_action(action_name=target or action_name, expected=expected_outcome)
                else:
                    exec_result = await physical_runtime.observe()

                success = exec_result.get("success", False)

                if success:
                    reflection = {
                        "status": "SUCCESS",
                        "strategy": "CONTINUE",
                        "reasoning": "Action executed and semantically verified."
                    }
                else:
                    reflection = {
                        "status": "FAILED",
                        "strategy": "ESCALATE_TO_USER",
                        "reasoning": exec_result.get("reason", "Verification failed after execution.")
                    }
                    task_success = False

                if step_idx == 0:
                     self.progressor.start_task(task_id, plan.get("summary", user_prompt), [step], active_app)
                progress_info = self.progressor.update_step(task_id, step_idx, action_name, reflection)

                executed_trajectory.append({
                    "step": step_idx,
                    "action": action_name,
                    "target": target,
                    "status": reflection["status"],
                    "reflection": reflection
                })

                yield {
                    "type": "LOG_STEP",
                    "step": "ACTION_LOOP",
                    "title": f"Closed-Loop Execute: Step {step_idx+1}/{len(steps_list)}",
                    "description": f"Action: {action_name} -> {target}. Verified: {exec_result.get('success')}",
                    "payload": {
                        "step_index": step_idx,
                        "action": step,
                        "reflection": reflection,
                        "progress": progress_info,
                        "execution_result": exec_result
                    }
                }

                if not exec_result.get("success"):
                    yield {
                        "type": "CHARACTER_STATE",
                        "state": "ERROR",
                        "speech": f"I encountered an error during execution: {reflection['reasoning']}"
                    }
                    break

            # Module 2.1 & 2.3: Trajectory Reflector Learning Extraction
            # ONLY record successful trajectories (Do not pollute RAG memory with failures)
            if task_success and executed_trajectory:
                trajectory_learning = self.trajectory_reflector.extract_learnings(
                    user_goal=user_prompt,
                    trajectory_steps=executed_trajectory,
                    final_state={"app": active_app, "title": screen_title},
                    app_name=active_app
                )
                self.app_memory.record_successful_trajectory(
                    app=active_app,
                    task=user_prompt,
                    steps=steps_list,
                    tenant_id=user_id
                )

                # Reinforce personal habit in flywheel & QwenPaw ReMe Layer 3
                learn_res = self.flywheel.record_interaction(
                    user_id=user_id,
                    domain=plan.get("domain", "general"),
                    selection=plan.get("summary", ""),
                    feedback_type="CONFIRMED_SELECTION"
                )
                self.reme.auto_memory_evolve(f"Confirmed preference in {plan.get('domain', 'general')}: {plan.get('summary')}")

                yield {
                    "type": "LOG_STEP",
                    "step": "LEARNING",
                    "title": "Flywheel, App RAG & ReMe Memory Updated",
                    "description": f"Updated confidence for '{learn_res.get('text', 'Habit')}': {learn_res.get('new_confidence')}. Stored verified trajectory.",
                    "payload": {
                        "flywheel": learn_res,
                        "trajectory_learning": trajectory_learning,
                        "reme_working_steps": self.reme.working_memory["current_step"]
                    }
                }

            # Generate Neural Voice Speech Response
            final_status = "completed" if task_success else "encountered issues with"
            speech_response = f"Done! I've {final_status}: {plan['summary']}."
            audio_uri = None
            try:
                audio_uri = await self.tts.generate_audio_base64(speech_response)
            except Exception as e:
                print(f"TTS error: {e}")

            yield {
                "type": "CHARACTER_STATE",
                "state": "SUCCESS" if task_success else "ERROR",
                "speech": speech_response,
                "audio_data_uri": audio_uri
            }
            yield {
                "type": "LOG_STEP",
                "step": "EXPLAIN",
                "title": "Task Explanation & Verified Result",
                "description": speech_response,
                "payload": {"has_neural_voice": audio_uri is not None}
            }

            self.memory.log_action_audit(user_id, plan.get("intent", "task"), plan["summary"], risk_tier, task_success)

    def _execute_plan_tools(self, plan: Dict[str, Any], screen_context: Any) -> Dict[str, Any]:
        # Hardcoded demo intents (book_movie, order_food) have been removed.
        # Now generic action routing occurs here.
        steps = plan.get("steps", [])
        if not steps:
            return {"status": "SUCCESS", "message": "No actions to execute."}
            
        step = steps[0]
        action_name = step.get("action", "").lower()
        target = step.get("target", "")

        if action_name in ["open_app", "launch_app"]:
            return execute_tool("launch_app", {"app_name": target})
        elif action_name == "tap":
            return {"status": "SUCCESS", "message": f"Physical tap intended on '{target}'"}
        elif action_name == "input_text":
            return {"status": "SUCCESS", "message": f"Input text intended: '{target}'"}
        elif action_name == "scroll":
            return {"status": "SUCCESS", "message": f"Scroll intended: '{target}'"}
            
        return {"status": "SUCCESS", "message": f"Action '{action_name}' registered."}
