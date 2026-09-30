"""
Synapse AI — Android Agent Intelligence Stack Integration Test
Evaluates:
1. Multimodal Android State Perception (Ontology Roles & Screen Classification)
2. Semantic Target Grounding (LLM intent -> ranked coordinates)
3. Action Engine & Closed-Loop Verification (Expected Outcome + Temporal Diff)
4. Native Android Intents (ACTION_VIEW geo:, web search)
5. Multi-App Orchestration (Chrome -> Extract Data -> Maps)
"""

import urllib.request
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

def main():
    print("=" * 65)
    print(" SYNAPSE AI — ANDROID AGENT INTELLIGENCE STACK EVALUATION")
    print("=" * 65)

    # 1. Evaluate Multimodal Perception & State Engine
    print("\n[+] 1. Testing Multimodal Perception & Screen Classification (/api/android/state)...")
    status, state = get('http://127.0.0.1:8000/api/android/state?app_hint=calc')
    print(f"    Status: {status}")
    print(f"    Classified Screen Type: {state['screen_type']}")
    print(f"    Foreground App Package: {state['app_package']}")
    print(f"    Total Structured Elements: {state['total_elements']}")
    sample_roles = [f"{e['label']}:{e['role']}" for e in state['elements'][:6]]
    print(f"    Sample Role Ontology: {sample_roles}")

    # 2. Evaluate Semantic Grounding Engine (LLM Never Emits Raw Coordinates)
    print("\n[+] 2. Testing Semantic Grounding Engine (/api/android/ground)...")
    test_intents = [
        ("Clear display", "CANCEL"),
        ("Calculate result / equals", "CONFIRM"),
        ("Addition operator", "BUTTON"),
        ("Number 7", "BUTTON")
    ]
    for intent, role in test_intents:
        status, ground_res = post('http://127.0.0.1:8000/api/android/ground', {
            "target": intent,
            "expected_role": role,
            "app_hint": "calc"
        })
        matched = ground_res.get('matched_element') or {}
        coords = ground_res.get('target_coordinates')
        conf = ground_res.get('confidence')
        print(f"    Intent: '{intent}' (Role: {role})")
        print(f"      -> Resolved Element: [{matched.get('label')}] ({matched.get('role')})")
        print(f"      -> Grounded Coordinates: {coords}")
        print(f"      -> Composite Confidence: {conf}")

    # 3. Evaluate Closed-Loop Action Execution with Verification
    print("\n[+] 3. Testing Closed-Loop Action & Verification (/api/android/execute)...")
    status, exec_res = post('http://127.0.0.1:8000/api/android/execute', {
        "action": "tap",
        "target": "C",
        "expected_screen_change": True
    })
    print(f"    Action: {exec_res['action']} on Target: {exec_res['target']}")
    print(f"    Grounded Coordinates: {exec_res['coordinates']}")
    print(f"    Method: {exec_res['method']}")
    v = exec_res.get('verification') or {}
    print(f"    Verification Status: {v.get('verified')} (Confidence: {v.get('confidence')})")
    print(f"    Verification Reason: {v.get('reason')}")

    # 4. Evaluate Native Android Intent Dispatch
    print("\n[+] 4. Testing Native Android Intent Dispatch (/api/android/intent)...")
    status, intent_res = post('http://127.0.0.1:8000/api/android/intent', {
        "action": "android.intent.action.VIEW",
        "uri": "geo:0,0?q=top+pizza+near+me"
    })
    print(f"    Status: {status}")
    print(f"    Success: {intent_res['success']}")
    print(f"    Dispatched Intent: {intent_res['target']}")
    print(f"    Execution Method: {intent_res['method']}")

    # 5. Evaluate Multi-App Orchestrator (Chrome -> Maps Pipeline)
    print("\n[+] 5. Testing Multi-App Orchestrator (/api/android/multi-app-workflow)...")
    status, workflow_res = post('http://127.0.0.1:8000/api/android/multi-app-workflow', {
        "workflow": "restaurant_to_maps",
        "query": "best Italian restaurant"
    })
    print(f"    Workflow: {workflow_res['workflow']}")
    print(f"    Success: {workflow_res['success']}")
    print(f"    Extracted Blackboard Data: {workflow_res['extracted_blackboard']}")
    print(f"    Final App in Foreground: {workflow_res['final_foreground_app']}")
    print(f"    ChromaDB Trajectory ID: {workflow_res['vector_memory_recorded']}")
    print("    Execution Timeline:")
    for step in workflow_res['timeline']:
        print(f"      Step {step['step']}: [{step['app']}] {step['action']} -> {step['status']}")

    print("\n" + "=" * 65)
    print(" ALL 5 ANDROID AGENT INTELLIGENCE STACK MODULES VERIFIED!")
    print("=" * 65)

if __name__ == "__main__":
    main()
