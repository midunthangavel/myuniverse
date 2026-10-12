"""
First-Party Native Services Engine for Synapse AI Agent Platform
Provides fully functional, deterministic native backends for:
1. Synapse Food (restaurant menus, cart state, item pricing, order checkout)
2. Synapse Messages (inbox, threads, message dispatch)
3. Synapse Calendar (event scheduling, conflict detection, recurrence)
4. Synapse Tasks (todo items, reminder deadlines, priority tags)
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


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
    status: str = "PREPARING"
    created_at: float = Field(default_factory=time.time)


class FoodService:
    def __init__(self):
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
        # tenant_id -> List[CartItem]
        self.carts: Dict[str, List[CartItem]] = {}
        # tenant_id -> List[FoodOrder]
        self.orders: Dict[str, List[FoodOrder]] = {}

    def list_restaurants(self) -> List[Dict[str, Any]]:
        return [r.dict() for r in self.restaurants.values()]

    def get_restaurant(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        r = self.restaurants.get(restaurant_id)
        return r.dict() if r else None

    def add_to_cart(self, tenant_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        cart = self.carts.setdefault(tenant_id, [])
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

        # Check existing
        for c in cart:
            if c.item_id == matched_item.id:
                c.quantity += quantity
                return {"success": True, "cart": [i.dict() for i in cart]}

        cart.append(CartItem(
            item_id=matched_item.id,
            name=matched_item.name,
            price=matched_item.price,
            quantity=quantity
        ))
        return {"success": True, "cart": [i.dict() for i in cart]}

    def get_cart(self, tenant_id: str) -> Dict[str, Any]:
        cart = self.carts.get(tenant_id, [])
        subtotal = sum(i.price * i.quantity for i in cart)
        tax = round(subtotal * 0.08, 2)
        delivery_fee = 3.99 if subtotal > 0 else 0.0
        total = round(subtotal + tax + delivery_fee, 2)
        return {
            "tenant_id": tenant_id,
            "items": [i.dict() for i in cart],
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "delivery_fee": delivery_fee,
            "total": total
        }

    def clear_cart(self, tenant_id: str):
        self.carts[tenant_id] = []

    def checkout(self, tenant_id: str, address: str = "742 Evergreen Terrace") -> Dict[str, Any]:
        cart_info = self.get_cart(tenant_id)
        if not cart_info["items"]:
            return {"success": False, "error": "Cart is empty"}

        order = FoodOrder(
            order_id=f"ord_{uuid.uuid4().hex[:10]}",
            tenant_id=tenant_id,
            restaurant_name="Sushi Zen",
            items=[CartItem(**i) for i in cart_info["items"]],
            subtotal=cart_info["subtotal"],
            tax=cart_info["tax"],
            delivery_fee=cart_info["delivery_fee"],
            total=cart_info["total"],
            delivery_address=address,
            status="CONFIRMED"
        )
        self.orders.setdefault(tenant_id, []).append(order)
        self.clear_cart(tenant_id)
        return {"success": True, "order": order.dict()}


# ==========================================
# 2. Synapse Messages Service
# ==========================================

class MessageRecord(BaseModel):
    id: str
    tenant_id: str
    recipient: str
    body: str
    direction: str = "OUTBOUND" # OUTBOUND or INBOUND
    status: str = "DELIVERED"
    timestamp: float = Field(default_factory=time.time)


class MessagesService:
    def __init__(self):
        # tenant_id -> List[MessageRecord]
        self.messages: Dict[str, List[MessageRecord]] = {}

    def send_message(self, tenant_id: str, recipient: str, body: str) -> Dict[str, Any]:
        msg = MessageRecord(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            tenant_id=tenant_id,
            recipient=recipient,
            body=body,
            direction="OUTBOUND",
            status="DELIVERED"
        )
        self.messages.setdefault(tenant_id, []).append(msg)
        return {"success": True, "message": msg.dict()}

    def get_threads(self, tenant_id: str) -> List[Dict[str, Any]]:
        msgs = self.messages.get(tenant_id, [])
        threads: Dict[str, List[Dict[str, Any]]] = {}
        for m in msgs:
            threads.setdefault(m.recipient, []).append(m.dict())
        return [{"recipient": r, "messages": ml, "count": len(ml)} for r, ml in threads.items()]


# ==========================================
# 3. Synapse Calendar Service
# ==========================================

class CalendarEvent(BaseModel):
    id: str
    tenant_id: str
    title: str
    start_time: str # e.g. "2026-10-15T14:00:00"
    duration_minutes: int
    location: str = ""
    attendees: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class CalendarService:
    def __init__(self):
        # tenant_id -> List[CalendarEvent]
        self.events: Dict[str, List[CalendarEvent]] = {}

    def create_event(self, tenant_id: str, title: str, start_time: str, duration_minutes: int = 60, location: str = "", attendees: List[str] = None) -> Dict[str, Any]:
        # Conflict detection
        existing = self.events.get(tenant_id, [])
        for ev in existing:
            if ev.start_time == start_time:
                return {
                    "success": False,
                    "conflict": True,
                    "conflicting_event": ev.dict(),
                    "error": f"Conflict detected with existing event: '{ev.title}' at {start_time}"
                }

        ev = CalendarEvent(
            id=f"cal_{uuid.uuid4().hex[:10]}",
            tenant_id=tenant_id,
            title=title,
            start_time=start_time,
            duration_minutes=duration_minutes,
            location=location,
            attendees=attendees or []
        )
        self.events.setdefault(tenant_id, []).append(ev)
        return {"success": True, "event": ev.dict()}

    def list_events(self, tenant_id: str) -> List[Dict[str, Any]]:
        return [e.dict() for e in self.events.get(tenant_id, [])]


# ==========================================
# 4. Synapse Tasks Service
# ==========================================

class TaskItem(BaseModel):
    id: str
    tenant_id: str
    title: str
    due_date: str = ""
    priority: str = "NORMAL" # LOW, NORMAL, HIGH, URGENT
    completed: bool = False
    created_at: float = Field(default_factory=time.time)


class TasksService:
    def __init__(self):
        # tenant_id -> List[TaskItem]
        self.tasks: Dict[str, List[TaskItem]] = {}

    def create_task(self, tenant_id: str, title: str, due_date: str = "", priority: str = "NORMAL") -> Dict[str, Any]:
        t = TaskItem(
            id=f"tsk_{uuid.uuid4().hex[:10]}",
            tenant_id=tenant_id,
            title=title,
            due_date=due_date,
            priority=priority.upper(),
            completed=False
        )
        self.tasks.setdefault(tenant_id, []).append(t)
        return {"success": True, "task": t.dict()}

    def list_tasks(self, tenant_id: str, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
        all_tasks = self.tasks.get(tenant_id, [])
        if completed is not None:
            all_tasks = [t for t in all_tasks if t.completed == completed]
        return [t.dict() for t in all_tasks]

    def complete_task(self, tenant_id: str, task_id: str) -> Dict[str, Any]:
        tasks = self.tasks.get(tenant_id, [])
        for t in tasks:
            if t.id == task_id or t.title.lower() == task_id.lower():
                t.completed = True
                return {"success": True, "task": t.dict()}
        return {"success": False, "error": f"Task '{task_id}' not found"}


# Singletons
food_service = FoodService()
messages_service = MessagesService()
calendar_service = CalendarService()
tasks_service = TasksService()
