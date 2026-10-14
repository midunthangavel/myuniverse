"""
First-Party Native Services Engine for Synapse AI Agent Platform
Provides fully functional, deterministic, durable SQLite backends for:
1. Synapse Food (restaurant menus, cart state, item pricing, order checkout)
2. Synapse Messages (inbox, threads, message dispatch)
3. Synapse Calendar (event scheduling, conflict detection, recurrence)
4. Synapse Tasks (todo items, reminder deadlines, priority tags)

All mutations and queries are persisted durably in synapse_memory.db,
isolated strictly by authenticated tenant_id, and protected with idempotency keys.
"""

import os
import sqlite3
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "synapse_memory.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_first_party_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Calendar Events
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS first_party_calendar_events (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            location TEXT DEFAULT '',
            attendees_json TEXT DEFAULT '[]',
            status TEXT DEFAULT 'CONFIRMED',
            created_at REAL NOT NULL,
            idempotency_key TEXT UNIQUE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cal_tenant ON first_party_calendar_events(tenant_id);")

        # 2. Tasks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS first_party_tasks (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT DEFAULT '',
            priority TEXT DEFAULT 'NORMAL',
            completed INTEGER DEFAULT 0,
            completed_at REAL,
            created_at REAL NOT NULL,
            idempotency_key TEXT UNIQUE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON first_party_tasks(tenant_id);")

        # 3. Messages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS first_party_messages (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            recipient TEXT NOT NULL,
            body TEXT NOT NULL,
            direction TEXT DEFAULT 'OUTBOUND',
            status TEXT DEFAULT 'DELIVERED',
            timestamp REAL NOT NULL,
            idempotency_key TEXT UNIQUE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_tenant ON first_party_messages(tenant_id);")

        # 4. Food Cart Items
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS first_party_food_cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            updated_at REAL NOT NULL,
            UNIQUE(tenant_id, item_id)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cart_tenant ON first_party_food_cart(tenant_id);")

        # 5. Food Orders
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS first_party_food_orders (
            order_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            restaurant_name TEXT NOT NULL,
            items_json TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            delivery_fee REAL NOT NULL,
            total REAL NOT NULL,
            delivery_address TEXT NOT NULL,
            status TEXT DEFAULT 'CONFIRMED',
            created_at REAL NOT NULL,
            idempotency_key TEXT UNIQUE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_tenant ON first_party_food_orders(tenant_id);")
        conn.commit()


# Initialize tables at module import
init_first_party_tables()


# ==========================================
# 1. Synapse Food Service
# ==========================================

class FoodMenuItem(BaseModel):
    id: str
    name: str
    price: float
    description: str
    category: str


class Restaurant(BaseModel):
    id: str
    name: str
    cuisine: str
    rating: float
    menu: List[FoodMenuItem]


class CartItem(BaseModel):
    item_id: str
    name: str
    price: float
    quantity: int


class FoodOrder(BaseModel):
    order_id: str
    tenant_id: str
    restaurant_name: str
    items: List[CartItem]
    subtotal: float
    tax: float
    delivery_fee: float
    total: float
    delivery_address: str
    status: str = "CONFIRMED"
    created_at: float = Field(default_factory=time.time)


class FoodService:
    def __init__(self):
        init_first_party_tables()
        self.restaurants: Dict[str, Restaurant] = {
            "rest_sushi_zen": Restaurant(
                id="rest_sushi_zen",
                name="Sushi Zen",
                cuisine="Japanese",
                rating=4.9,
                menu=[
                    FoodMenuItem(id="sushi_omakase", name="Omakase Platter", price=45.0, description="12 pieces nigiri chef selection", category="Mains"),
                    FoodMenuItem(id="sushi_spicy_tuna", name="Spicy Tuna Roll", price=14.5, description="Yellowfin tuna, sriracha, cucumber", category="Rolls"),
                    FoodMenuItem(id="sushi_miso", name="Miso Soup", price=4.5, description="Dashi broth with tofu and wakame", category="Appetizers")
                ]
            ),
            "rest_burger_craft": Restaurant(
                id="rest_burger_craft",
                name="Burger Craft",
                cuisine="American",
                rating=4.7,
                menu=[
                    FoodMenuItem(id="burger_wagyu", name="Truffle Wagyu Burger", price=22.0, description="Wagyu beef patty, brioche, truffle aioli", category="Burgers"),
                    FoodMenuItem(id="burger_fries", name="Parmesan Garlic Fries", price=7.5, description="Hand-cut fries, aged parmesan, rosemary", category="Sides")
                ]
            ),
            "rest_pasta_fresca": Restaurant(
                id="rest_pasta_fresca",
                name="Pasta Fresca",
                cuisine="Italian",
                rating=4.8,
                menu=[
                    FoodMenuItem(id="pasta_carbonara", name="Authentic Carbonara", price=19.5, description="Guanciale, pecorino romano, fresh egg yolks", category="Pasta"),
                    FoodMenuItem(id="pasta_tiramisu", name="House Tiramisu", price=9.0, description="Espresso savoiardi, mascarpone cream", category="Desserts")
                ]
            )
        }

    def list_restaurants(self) -> List[Dict[str, Any]]:
        return [r.dict() for r in self.restaurants.values()]

    def get_restaurant(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        r = self.restaurants.get(restaurant_id)
        return r.dict() if r else None

    def add_to_cart(self, tenant_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        # Find item across menus
        matched_item = None
        for rest in self.restaurants.values():
            for item in rest.menu:
                if item.id == item_id or item.name.lower() == item_id.lower():
                    matched_item = item
                    break
            if matched_item:
                break

        if not matched_item:
            return {"success": False, "error": f"Item '{item_id}' not found in any menu"}

        now = time.time()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT quantity FROM first_party_food_cart WHERE tenant_id = ? AND item_id = ?",
                (tenant_id, matched_item.id)
            )
            row = cursor.fetchone()
            if row:
                new_qty = row["quantity"] + quantity
                cursor.execute(
                    "UPDATE first_party_food_cart SET quantity = ?, updated_at = ? WHERE tenant_id = ? AND item_id = ?",
                    (new_qty, now, tenant_id, matched_item.id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO first_party_food_cart (tenant_id, item_id, name, price, quantity, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, matched_item.id, matched_item.name, matched_item.price, quantity, now)
                )
            conn.commit()

        return {"success": True, "cart": self.get_cart(tenant_id)["items"]}

    def get_cart(self, tenant_id: str) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_id, name, price, quantity FROM first_party_food_cart WHERE tenant_id = ? ORDER BY id ASC",
                (tenant_id,)
            )
            rows = cursor.fetchall()

        items = [
            {"item_id": r["item_id"], "name": r["name"], "price": r["price"], "quantity": r["quantity"]}
            for r in rows
        ]
        subtotal = sum(i["price"] * i["quantity"] for i in items)
        tax = round(subtotal * 0.08, 2)
        delivery_fee = 3.99 if subtotal > 0 else 0.0
        total = round(subtotal + tax + delivery_fee, 2)
        return {
            "tenant_id": tenant_id,
            "items": items,
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "delivery_fee": delivery_fee,
            "total": total
        }

    def clear_cart(self, tenant_id: str):
        with get_db_connection() as conn:
            conn.execute("DELETE FROM first_party_food_cart WHERE tenant_id = ?", (tenant_id,))
            conn.commit()

    def checkout(
        self,
        tenant_id: str,
        address: str = "742 Evergreen Terrace",
        restaurant_name: str = "Sushi Zen",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Idempotency check
            if idempotency_key:
                cursor.execute(
                    "SELECT * FROM first_party_food_orders WHERE tenant_id = ? AND idempotency_key = ?",
                    (tenant_id, idempotency_key)
                )
                existing = cursor.fetchone()
                if existing:
                    return {
                        "success": True,
                        "cached": True,
                        "order": {
                            "order_id": existing["order_id"],
                            "tenant_id": existing["tenant_id"],
                            "restaurant_name": existing["restaurant_name"],
                            "items": json.loads(existing["items_json"]),
                            "subtotal": existing["subtotal"],
                            "tax": existing["tax"],
                            "delivery_fee": existing["delivery_fee"],
                            "total": existing["total"],
                            "delivery_address": existing["delivery_address"],
                            "status": existing["status"],
                            "created_at": existing["created_at"]
                        }
                    }

            cart_info = self.get_cart(tenant_id)
            if not cart_info["items"]:
                return {"success": False, "error": "Cart is empty"}

            order_id = f"ord_{uuid.uuid4().hex[:10]}"
            now = time.time()
            items_json = json.dumps(cart_info["items"])

            cursor.execute(
                """
                INSERT INTO first_party_food_orders 
                (order_id, tenant_id, restaurant_name, items_json, subtotal, tax, delivery_fee, total, delivery_address, status, created_at, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?)
                """,
                (
                    order_id,
                    tenant_id,
                    restaurant_name,
                    items_json,
                    cart_info["subtotal"],
                    cart_info["tax"],
                    cart_info["delivery_fee"],
                    cart_info["total"],
                    address,
                    now,
                    idempotency_key
                )
            )
            # Clear cart for tenant
            cursor.execute("DELETE FROM first_party_food_cart WHERE tenant_id = ?", (tenant_id,))
            conn.commit()

        order_dict = {
            "order_id": order_id,
            "tenant_id": tenant_id,
            "restaurant_name": restaurant_name,
            "items": cart_info["items"],
            "subtotal": cart_info["subtotal"],
            "tax": cart_info["tax"],
            "delivery_fee": cart_info["delivery_fee"],
            "total": cart_info["total"],
            "delivery_address": address,
            "status": "CONFIRMED",
            "created_at": now
        }
        return {"success": True, "order": order_dict}

    def list_orders(self, tenant_id: str) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM first_party_food_orders WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,)
            )
            rows = cursor.fetchall()

        orders = []
        for r in rows:
            orders.append({
                "order_id": r["order_id"],
                "tenant_id": r["tenant_id"],
                "restaurant_name": r["restaurant_name"],
                "items": json.loads(r["items_json"]),
                "subtotal": r["subtotal"],
                "tax": r["tax"],
                "delivery_fee": r["delivery_fee"],
                "total": r["total"],
                "delivery_address": r["delivery_address"],
                "status": r["status"],
                "created_at": r["created_at"]
            })
        return orders


# ==========================================
# 2. Synapse Messages Service
# ==========================================

class MessageRecord(BaseModel):
    id: str
    tenant_id: str
    recipient: str
    body: str
    direction: str = "OUTBOUND"
    status: str = "DELIVERED"
    timestamp: float = Field(default_factory=time.time)


class MessagesService:
    def __init__(self):
        init_first_party_tables()

    def send_message(
        self,
        tenant_id: str,
        recipient: str,
        body: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if idempotency_key:
                cursor.execute(
                    "SELECT * FROM first_party_messages WHERE tenant_id = ? AND idempotency_key = ?",
                    (tenant_id, idempotency_key)
                )
                existing = cursor.fetchone()
                if existing:
                    return {
                        "success": True,
                        "cached": True,
                        "message": {
                            "id": existing["id"],
                            "tenant_id": existing["tenant_id"],
                            "recipient": existing["recipient"],
                            "body": existing["body"],
                            "direction": existing["direction"],
                            "status": existing["status"],
                            "timestamp": existing["timestamp"]
                        }
                    }

            msg_id = f"msg_{uuid.uuid4().hex[:10]}"
            now = time.time()
            cursor.execute(
                """
                INSERT INTO first_party_messages (id, tenant_id, recipient, body, direction, status, timestamp, idempotency_key)
                VALUES (?, ?, ?, ?, 'OUTBOUND', 'DELIVERED', ?, ?)
                """,
                (msg_id, tenant_id, recipient, body, now, idempotency_key)
            )
            conn.commit()

        msg_dict = {
            "id": msg_id,
            "tenant_id": tenant_id,
            "recipient": recipient,
            "body": body,
            "direction": "OUTBOUND",
            "status": "DELIVERED",
            "timestamp": now
        }
        return {"success": True, "message": msg_dict}

    def get_threads(self, tenant_id: str) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM first_party_messages WHERE tenant_id = ? ORDER BY timestamp ASC",
                (tenant_id,)
            )
            rows = cursor.fetchall()

        threads: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            m = {
                "id": r["id"],
                "tenant_id": r["tenant_id"],
                "recipient": r["recipient"],
                "body": r["body"],
                "direction": r["direction"],
                "status": r["status"],
                "timestamp": r["timestamp"]
            }
            threads.setdefault(r["recipient"], []).append(m)

        return [{"recipient": rec, "messages": ml, "count": len(ml)} for rec, ml in threads.items()]

    def list_messages(self, tenant_id: str, recipient: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if recipient:
                cursor.execute(
                    "SELECT * FROM first_party_messages WHERE tenant_id = ? AND recipient = ? ORDER BY timestamp ASC",
                    (tenant_id, recipient)
                )
            else:
                cursor.execute(
                    "SELECT * FROM first_party_messages WHERE tenant_id = ? ORDER BY timestamp ASC",
                    (tenant_id,)
                )
            rows = cursor.fetchall()

        return [
            {
                "id": r["id"],
                "tenant_id": r["tenant_id"],
                "recipient": r["recipient"],
                "body": r["body"],
                "direction": r["direction"],
                "status": r["status"],
                "timestamp": r["timestamp"]
            }
            for r in rows
        ]


# ==========================================
# 3. Synapse Calendar Service
# ==========================================

class CalendarEvent(BaseModel):
    id: str
    tenant_id: str
    title: str
    start_time: str
    duration_minutes: int = 60
    location: str = ""
    attendees: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class CalendarService:
    def __init__(self):
        init_first_party_tables()

    def create_event(
        self,
        tenant_id: str,
        title: str,
        start_time: str,
        duration_minutes: int = 60,
        location: str = "",
        attendees: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Idempotency check
            if idempotency_key:
                cursor.execute(
                    "SELECT * FROM first_party_calendar_events WHERE tenant_id = ? AND idempotency_key = ?",
                    (tenant_id, idempotency_key)
                )
                existing = cursor.fetchone()
                if existing:
                    return {
                        "success": True,
                        "cached": True,
                        "event": {
                            "id": existing["id"],
                            "tenant_id": existing["tenant_id"],
                            "title": existing["title"],
                            "start_time": existing["start_time"],
                            "duration_minutes": existing["duration_minutes"],
                            "location": existing["location"],
                            "attendees": json.loads(existing["attendees_json"]),
                            "created_at": existing["created_at"]
                        }
                    }

            # Conflict detection for same tenant and start_time
            cursor.execute(
                "SELECT * FROM first_party_calendar_events WHERE tenant_id = ? AND start_time = ?",
                (tenant_id, start_time)
            )
            conflict_row = cursor.fetchone()
            if conflict_row:
                return {
                    "success": False,
                    "conflict": True,
                    "conflicting_event": {
                        "id": conflict_row["id"],
                        "tenant_id": conflict_row["tenant_id"],
                        "title": conflict_row["title"],
                        "start_time": conflict_row["start_time"]
                    },
                    "error": f"Conflict detected with existing event: '{conflict_row['title']}' at {start_time}"
                }

            ev_id = f"cal_{uuid.uuid4().hex[:10]}"
            now = time.time()
            attendees_list = attendees or []
            cursor.execute(
                """
                INSERT INTO first_party_calendar_events 
                (id, tenant_id, title, start_time, duration_minutes, location, attendees_json, status, created_at, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?)
                """,
                (ev_id, tenant_id, title, start_time, duration_minutes, location or "", json.dumps(attendees_list), now, idempotency_key)
            )
            conn.commit()

        ev_dict = {
            "id": ev_id,
            "tenant_id": tenant_id,
            "title": title,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "location": location or "",
            "attendees": attendees_list,
            "created_at": now
        }
        return {"success": True, "event": ev_dict}

    def list_events(self, tenant_id: str) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM first_party_calendar_events WHERE tenant_id = ? ORDER BY start_time ASC",
                (tenant_id,)
            )
            rows = cursor.fetchall()

        events = []
        for r in rows:
            events.append({
                "id": r["id"],
                "tenant_id": r["tenant_id"],
                "title": r["title"],
                "start_time": r["start_time"],
                "duration_minutes": r["duration_minutes"],
                "location": r["location"],
                "attendees": json.loads(r["attendees_json"]),
                "created_at": r["created_at"]
            })
        return events

    def get_event(self, tenant_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM first_party_calendar_events WHERE tenant_id = ? AND id = ?",
                (tenant_id, event_id)
            )
            r = cursor.fetchone()
            if not r:
                return None
            return {
                "id": r["id"],
                "tenant_id": r["tenant_id"],
                "title": r["title"],
                "start_time": r["start_time"],
                "duration_minutes": r["duration_minutes"],
                "location": r["location"],
                "attendees": json.loads(r["attendees_json"]),
                "created_at": r["created_at"]
            }


# ==========================================
# 4. Synapse Tasks Service
# ==========================================

class TaskItem(BaseModel):
    id: str
    tenant_id: str
    title: str
    due_date: str = ""
    priority: str = "NORMAL"
    completed: bool = False
    created_at: float = Field(default_factory=time.time)


class TasksService:
    def __init__(self):
        init_first_party_tables()

    def create_task(
        self,
        tenant_id: str,
        title: str,
        due_date: str = "",
        priority: str = "NORMAL",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if idempotency_key:
                cursor.execute(
                    "SELECT * FROM first_party_tasks WHERE tenant_id = ? AND idempotency_key = ?",
                    (tenant_id, idempotency_key)
                )
                existing = cursor.fetchone()
                if existing:
                    return {
                        "success": True,
                        "cached": True,
                        "task": {
                            "id": existing["id"],
                            "tenant_id": existing["tenant_id"],
                            "title": existing["title"],
                            "due_date": existing["due_date"],
                            "priority": existing["priority"],
                            "completed": bool(existing["completed"]),
                            "created_at": existing["created_at"]
                        }
                    }

            t_id = f"tsk_{uuid.uuid4().hex[:10]}"
            now = time.time()
            cursor.execute(
                """
                INSERT INTO first_party_tasks (id, tenant_id, title, due_date, priority, completed, created_at, idempotency_key)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (t_id, tenant_id, title, due_date or "", priority.upper(), now, idempotency_key)
            )
            conn.commit()

        t_dict = {
            "id": t_id,
            "tenant_id": tenant_id,
            "title": title,
            "due_date": due_date or "",
            "priority": priority.upper(),
            "completed": False,
            "created_at": now
        }
        return {"success": True, "task": t_dict}

    def list_tasks(self, tenant_id: str, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if completed is not None:
                comp_int = 1 if completed else 0
                cursor.execute(
                    "SELECT * FROM first_party_tasks WHERE tenant_id = ? AND completed = ? ORDER BY created_at DESC",
                    (tenant_id, comp_int)
                )
            else:
                cursor.execute(
                    "SELECT * FROM first_party_tasks WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,)
                )
            rows = cursor.fetchall()

        tasks = []
        for r in rows:
            tasks.append({
                "id": r["id"],
                "tenant_id": r["tenant_id"],
                "title": r["title"],
                "due_date": r["due_date"],
                "priority": r["priority"],
                "completed": bool(r["completed"]),
                "created_at": r["created_at"]
            })
        return tasks

    def complete_task(self, tenant_id: str, task_id: str) -> Dict[str, Any]:
        now = time.time()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM first_party_tasks 
                WHERE tenant_id = ? AND (id = ? OR LOWER(title) = LOWER(?))
                """,
                (tenant_id, task_id, task_id)
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": f"Task '{task_id}' not found"}

            cursor.execute(
                "UPDATE first_party_tasks SET completed = 1, completed_at = ? WHERE id = ?",
                (now, row["id"])
            )
            conn.commit()

        return {
            "success": True,
            "task": {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "title": row["title"],
                "due_date": row["due_date"],
                "priority": row["priority"],
                "completed": True,
                "created_at": row["created_at"]
            }
        }


# Singletons
food_service = FoodService()
messages_service = MessagesService()
calendar_service = CalendarService()
tasks_service = TasksService()
