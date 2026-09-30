"""
Automated Verification Test Suite for Wave 1 Foundation Upgrades:
- Module 1.1: Universal LLM Factory
- Module 1.2: Decorator-Based Tool Registry
- Module 1.3: YAML Prompt Template System
- Wave 1 REST Endpoints
"""

import asyncio
from app.llm_factory import llm_factory, get_llm
from app.tool_registry import tool_registry, list_registered_tools, execute_tool
from app.prompt_manager import prompt_manager, render_prompt
from app.main import app

def test_llm_factory():
    print("--> Testing Module 1.1: Universal LLM Factory...")
    providers = llm_factory.list_providers()
    assert len(providers) >= 5, f"Expected >= 5 providers, got {len(providers)}"
    provider_ids = [p["id"] for p in providers]
    for expected in ["builtin", "ollama", "openai", "vllm", "dashscope", "anthropic"]:
        assert expected in provider_ids, f"Provider '{expected}' not found in {provider_ids}"
    
    # Test fallback & builtin reasoning
    builtin = llm_factory.get_llm({"provider": "builtin"})
    health = asyncio.run(builtin.health_check())
    assert health["status"] == "online"

    # Test movie plan
    movie_plan = asyncio.run(builtin.plan_task("Book movie tickets tonight", [{"text": "Palladium IMAX"}]))
    assert movie_plan["intent"] == "book_movie"
    assert "steps" in movie_plan and len(movie_plan["steps"]) > 0

    # Test food plan
    food_plan = asyncio.run(builtin.plan_task("Order biryani for dinner", []))
    assert food_plan["intent"] == "order_food"

    print("    [PASS] Universal LLM Factory operates as expected.")

def test_tool_registry():
    print("--> Testing Module 1.2: Decorator-Based Tool Registry...")
    tools = list_registered_tools()
    assert len(tools) >= 12, f"Expected >= 12 tools registered, got {len(tools)}"
    
    tool_names = [t["function"]["name"] for t in tools]
    required_tools = [
        "tap_element", "swipe_screen", "input_text", "launch_app",
        "navigate_back", "take_screenshot", "schedule_meeting",
        "analyze_screen", "web_search", "send_notification",
        "search_movies", "search_food"
    ]
    for req in required_tools:
        assert req in tool_names, f"Required tool '{req}' not registered"

    # Test tap execution
    tap_res = execute_tool("tap_element", {"target": "Seat F14", "x": 0.52, "y": 0.41})
    assert tap_res["success"] is True
    assert tap_res["action"] == "TAP"

    # Test swipe execution
    swipe_res = execute_tool("swipe_screen", {"direction": "up", "distance": 500})
    assert swipe_res["success"] is True
    assert swipe_res["direction"] == "up"

    # Test launch app execution
    app_res = execute_tool("launch_app", {"app_name": "pulse_ride"})
    assert app_res["success"] is True
    assert "PulseRide" in app_res["app_name"]

    print("    [PASS] Decorator-Based Tool Registry operates as expected.")

def test_prompt_manager():
    print("--> Testing Module 1.3: YAML Prompt Template System...")
    templates = prompt_manager.list_templates()
    assert len(templates) >= 11, f"Expected >= 11 templates, got {len(templates)}"
    
    required_templates = [
        "system1_classifier", "task_planner", "action_operator",
        "reflector", "progressor", "governance_evaluator",
        "web_researcher", "screen_describer", "habit_analyzer",
        "morning_briefing", "trajectory_reflector"
    ]
    for req in required_templates:
        assert req in templates, f"Required template '{req}' not found"

    # Test reflector rendering
    reflector_text = render_prompt(
        "reflector",
        active_app="BiteGo",
        intended_action="TAP 'Add Biryani'",
        before_state="Menu list visible",
        after_state="Cart count: 1 item"
    )
    assert "BiteGo" in reflector_text
    assert "Add Biryani" in reflector_text
    assert "Status: SUCCESS" in reflector_text

    # Test task planner rendering
    planner_text = render_prompt(
        "task_planner",
        active_app="PulseRide",
        memories="Learned preference: Premier ride",
        screen_context="Ride booking screen",
        user_query="Book ride to office"
    )
    assert "PulseRide" in planner_text
    assert "Book ride to office" in planner_text

    print("    [PASS] YAML Prompt Template System operates as expected.")

def test_fastapi_endpoints():
    print("--> Testing Wave 1 REST Endpoints...")
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "Universal Factory Active" in data["llm_factory"]
    assert "Primitives Registered" in data["tool_registry"]
    assert "YAML Templates Loaded" in data["prompt_manager"]

    # LLM providers
    res = client.get("/api/llm/providers")
    assert res.status_code == 200
    assert len(res.json()["providers"]) >= 5

    # Tools
    res = client.get("/api/tools")
    assert res.status_code == 200
    assert res.json()["total_tools"] >= 12

    # Prompts
    res = client.get("/api/prompts")
    assert res.status_code == 200
    assert res.json()["total_templates"] >= 11

    # Render prompt endpoint
    res = client.post("/api/prompts/render", json={
        "template": "reflector",
        "variables": {
            "active_app": "CinePass",
            "intended_action": "Select F15",
            "before_state": "Empty",
            "after_state": "Selected"
        }
    })
    assert res.status_code == 200
    assert "CinePass" in res.json()["rendered"]

    # Execute tool endpoint
    res = client.post("/api/tools/execute", json={
        "name": "tap_element",
        "params": {"target": "Checkout Button"}
    })
    assert res.status_code == 200
    assert res.json()["success"] is True

    print("    [PASS] Wave 1 REST Endpoints verified successfully.")

if __name__ == "__main__":
    test_llm_factory()
    test_tool_registry()
    test_prompt_manager()
    test_fastapi_endpoints()
    print("\n==============================================")
    print("ALL WAVE 1 FOUNDATION TESTS PASSED (100% OK)")
    print("==============================================")
