"""
Extract and parse recent Gmail emails from the connected Android device.
"""
import sys
import os
import asyncio
import json

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.device.android_controller import AndroidADBController

async def parse_gmail():
    ctrl = AndroidADBController()
    ui_res = await ctrl.get_ui_hierarchy()
    nodes = ui_res.get("nodes", [])

    emails = []
    current_email = None

    for node in nodes:
        rid = (node.get("resource_id") or "").strip()
        txt = (node.get("text") or "").strip()
        desc = (node.get("content_desc") or "").strip()
        bounds = node.get("bounds", {})

        if "viewified_conversation_item_view" in rid:
            if current_email:
                emails.append(current_email)
            current_email = {
                "bounds": bounds,
                "sender": "",
                "subject": "",
                "snippet": "",
                "date": "",
                "unread": False,
                "raw_fields": {}
            }
            continue

        if current_email is not None:
            # Check if this node is still within or belongs to this email
            # Sometimes date or other views have specific resource IDs
            if "senders" in rid:
                current_email["sender"] = txt or desc
            elif "subject" in rid:
                current_email["subject"] = txt or desc
            elif "snippet" in rid:
                current_email["snippet"] = txt or desc
            elif "date" in rid:
                current_email["date"] = txt or desc
            else:
                # Store any other fields
                if rid:
                    field_name = rid.split("/")[-1]
                    current_email["raw_fields"][field_name] = txt or desc

    if current_email:
        emails.append(current_email)

    output_path = os.path.join(os.path.dirname(__file__), "extracted_gmail.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)

    print(f"Extracted {len(emails)} emails. Saved to {output_path}")
    for idx, em in enumerate(emails[:5], 1):
        print(f"\n--- Email {idx} ---")
        print(f"Sender : {em.get('sender')}")
        print(f"Date   : {em.get('date')}")
        print(f"Subject: {em.get('subject')}")
        print(f"Snippet: {em.get('snippet')}")
        print(f"Fields : {em.get('raw_fields')}")

if __name__ == "__main__":
    asyncio.run(parse_gmail())
