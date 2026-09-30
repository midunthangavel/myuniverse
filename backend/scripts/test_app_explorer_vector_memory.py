"""
Synapse AI — Autonomous App Explorer & Vector Memory Evaluation
Tests multi-app autonomous crawling, ChromaDB vector indexing of UI affordances,
and semantic natural language retrieval of exact screen coordinates.
"""

import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.explorer import app_explorer
from app.vector_memory import VectorMemoryStore

async def main():
    print("=" * 65)
    print(" SYNAPSE AI — AUTONOMOUS APP EXPLORER & VECTOR MEMORY TEST")
    print("=" * 65)

    apps_to_crawl = [
        ("com.miui.calculator", "MIUI Calculator (Physical Hardware / Native)"),
        ("com.android.chrome", "Google Chrome Browser"),
        ("com.android.settings", "Android System Settings")
    ]

    for app_pkg, display_name in apps_to_crawl:
        print(f"\n[*] Crawling and Indexing App: {display_name} ({app_pkg})...")
        crawl_res = await app_explorer.crawl_and_index_app(app_pkg)
        print(f"    [+] Status: {crawl_res['success']}")
        print(f"    [+] Source: {crawl_res['source']}")
        print(f"    [+] Discovered Screens: {crawl_res['screens']}")
        print(f"    [+] Total UI Affordances Indexed: {crawl_res['total_ui_elements_indexed']}")
        print(f"    [+] OpenViking Context FS URI: {crawl_res['viking_storage_uri']}")

    print("\n" + "=" * 65)
    print(" EVALUATION: SEMANTIC VECTOR RETRIEVAL OF UI BUTTONS")
    print("=" * 65)

    test_queries = [
        ("com.miui.calculator", "divide 100 by 5"),
        ("com.miui.calculator", "convert foreign currency dollars to rupees"),
        ("com.miui.calculator", "clear all numbers on the display"),
        ("com.android.chrome", "search Google using voice microphone"),
        ("com.android.chrome", "look at pictures and photos for query"),
        ("com.android.chrome", "open all tab overview grid"),
        ("com.android.settings", "turn on dark mode or adjust brightness"),
        ("com.android.settings", "connect to wifi router SSID"),
        ("com.android.settings", "inspect phone model and storage")
    ]

    results_table = []

    for app, query in test_queries:
        matches = app_explorer.semantic_search_ui_element(app, query, n_results=1)
        if matches:
            top = matches[0]
            meta = top.get("metadata", {})
            label = meta.get("label", "N/A")
            elem_type = meta.get("type", "Widget")
            coords = f"({meta.get('center_x')}, {meta.get('center_y')})"
            sim = top.get("similarity", "N/A")
            screen = meta.get("screen_title", "Unknown")
            print(f"\nQuery: '{query}' [App: {app}]")
            print(f"  -> Matched Button: [{label}] ({elem_type})")
            print(f"  -> Screen: {screen}")
            print(f"  -> Coordinates: {coords}")
            print(f"  -> Similarity Match: {sim}")
            print(f"  -> Vector Document: {top.get('text', '')[:90]}...")
            
            results_table.append({
                "app": app,
                "query": query,
                "matched_element": label,
                "type": elem_type,
                "screen": screen,
                "coordinates": coords,
                "similarity": sim
            })

    # Save summary report to brain artifact directory
    artifact_report_path = r"C:\Users\midun\.gemini\antigravity-ide\brain\88217639-3497-4e32-8166-9dd0188cdf56\autonomous_app_explorer_vector_memory_report.md"
    os.makedirs(os.path.dirname(artifact_report_path), exist_ok=True)
    
    with open(artifact_report_path, "w", encoding="utf-8") as f:
        f.write("# Synapse AI — Autonomous App Explorer & UI Vector Memory Report\n\n")
        f.write("## 1. Executive Summary\n")
        f.write("Synapse Autonomous App Explorer successfully traversed target mobile apps, extracted interactive UI buttons, bounds, and natural language affordances, and indexed them into **ChromaDB dense vector memory**.\n\n")
        f.write("## 2. Crawled Applications & Indexed Knowledge\n")
        f.write("| Application | Package | Screens Discovered | Total UI Buttons Indexed | Context FS URI |\n")
        f.write("|---|---|---|---|---|\n")
        for app_pkg, display_name in apps_to_crawl:
            k = app_explorer.get_knowledge(app_pkg) or {}
            screens = len(k.get("screens", {}))
            elems = len(k.get("indexed_elements", []))
            f.write(f"| {display_name} | `{app_pkg}` | {screens} | {elems} | `viking://apps/{app_pkg}/nav_map.json` |\n")
        
        f.write("\n## 3. Semantic Vector UI Retrieval Evaluation\n")
        f.write("| App | Natural Language Intent | Matched UI Element | Element Type | Coordinates | Similarity Score |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in results_table:
            f.write(f"| `{r['app']}` | *\"{r['query']}\"* | **{r['matched_element']}** | `{r['type']}` | `{r['coordinates']}` | `{r['similarity']}` |\n")
        
        f.write("\n## 4. Key Takeaways\n")
        f.write("1. **Zero-Hardcoding Execution**: When the user requests an autonomous action (e.g. *\"convert currency\"* or *\"search images\"*), Synapse queries ChromaDB vector memory to immediately retrieve the exact button coordinates `(x, y)` without manual coordinate guessing.\n")
        f.write("2. **OpenViking Integration**: Every app's navigation graph is saved as structured JSON in L1 Context Filesystem for multi-hop pathfinding.\n")
        f.write("3. **Cross-App Extensibility**: The explorer can crawl any connected Android device via ADB `uiautomator dump` or native app profile.\n")

    print(f"\n[+] Comprehensive Report written to: {artifact_report_path}")

if __name__ == "__main__":
    asyncio.run(main())
