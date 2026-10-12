"""
Vector Memory Engine using ChromaDB
Provides tenant-isolated dense semantic embeddings and similarity search for user preferences,
habits, and episodic context with complete namespace separation and cold-start bootstrapping.
"""

import os
import re
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

CHROMA_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

def _sanitize_collection_name(name: str) -> str:
    """ChromaDB collections require 3-63 alphanumeric chars or underscores."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", name).lower()
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if len(cleaned) < 3:
        cleaned = f"col_{cleaned}".ljust(3, "0")
    return cleaned[:63]


class VectorMemoryStore:
    def __init__(self, persist_dir: str = CHROMA_DATA_DIR):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.tenant_collections: Dict[str, Any] = {}

    @property
    def collection(self):
        """Backward compatibility property returning the default tenant collection."""
        return self.get_or_create_tenant_collection("user_default")

    def get_or_create_tenant_collection(self, tenant_id: str = "user_default"):
        """Returns or creates a strictly tenant-namespaced ChromaDB collection."""
        safe_tenant = _sanitize_collection_name(tenant_id)
        collection_name = f"syn_mem_{safe_tenant}"[:63]
        
        if collection_name in self.tenant_collections:
            return self.tenant_collections[collection_name]
            
        col = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"tenant_id": tenant_id, "type": "tenant_episodic_memory"}
        )
        self.tenant_collections[collection_name] = col
        return col

    def add_memory(self, doc_id: str, text: str, user_id: str = "user_default", metadata: Dict[str, Any] = None):
        """Adds or updates a memory in the tenant's isolated vector collection."""
        col = self.get_or_create_tenant_collection(user_id)
        meta = metadata or {}
        meta["tenant_id"] = user_id
        meta["user_id"] = user_id
        # Ensure primitive metadata values for ChromaDB
        cleaned_meta = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v for k, v in meta.items()}
        
        col.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[cleaned_meta]
        )

    def remove_memory(self, doc_id: str, user_id: str = "user_default"):
        try:
            col = self.get_or_create_tenant_collection(user_id)
            col.delete(ids=[doc_id])
        except Exception:
            pass

    def semantic_search(self, query: str, user_id: str = "user_default", n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Executes semantic vector similarity search strictly within the tenant's collection.
        Prevents any cross-tenant preference or context leakage.
        """
        col = self.get_or_create_tenant_collection(user_id)
        total = col.count()
        if total == 0:
            return []

        limit = min(n_results, total)
        try:
            results = col.query(
                query_texts=[query],
                n_results=limit
            )
        except Exception:
            return []

        matches = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                similarity = round(max(0, 1.0 - (dist / 2.0)) * 100, 1)
                matches.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": round(dist, 3),
                    "semantic_match": f"{similarity}%",
                    "type": meta.get("category", "SEMANTIC_MEMORY")
                })

        return matches

    def bootstrap_cold_start_profile(self, tenant_id: str, default_preferences: Optional[List[str]] = None) -> int:
        """
        Bootstraps initial context for a newly registered tenant if their collection is empty.
        Returns the number of seeded items.
        """
        col = self.get_or_create_tenant_collection(tenant_id)
        if col.count() > 0:
            return 0  # Tenant already has context, do not overwrite

        defaults = default_preferences or [
            "Default delivery address is 742 Evergreen Terrace",
            "Prefers quiet notifications after 9:00 PM",
            "Favorite cuisine: Japanese and Healthy Bowls",
            "Commute method: Metro or rideshare"
        ]

        for idx, pref in enumerate(defaults):
            self.add_memory(
                doc_id=f"cold_start_{idx}_{tenant_id}",
                text=pref,
                user_id=tenant_id,
                metadata={"category": "COLD_START_BOOTSTRAP", "source": "system_bootstrap"}
            )
        return len(defaults)

    def seed_from_sqlite(self, sqlite_profile: Dict[str, Any], user_id: str = "user_default"):
        """Indexes all memories from SQLite into the tenant's isolated vector collection."""
        for item in sqlite_profile.get("explicit", []):
            self.add_memory(
                doc_id=item["id"],
                text=f"Preference: {item['text']}",
                user_id=user_id,
                metadata={"category": "EXPLICIT", "source": "user_defined", "type": item.get("category", "General")}
            )

        for item in sqlite_profile.get("learned", []):
            self.add_memory(
                doc_id=item["id"],
                text=f"Learned Habit: {item['text']}",
                user_id=user_id,
                metadata={"category": "LEARNED", "confidence": item.get("confidence", "85%"), "source": "observed_behavior"}
            )

        for item in sqlite_profile.get("entities", []):
            self.add_memory(
                doc_id=item["id"],
                text=f"Entity {item.get('name')}: {item.get('role', '')} {item.get('address', '')}",
                user_id=user_id,
                metadata={"category": "ENTITY", "priority": item.get("priority", "Standard")}
            )

        for item in sqlite_profile.get("routines", []):
            self.add_memory(
                doc_id=item["id"],
                text=f"Schedule Routine {item.get('title')}: {item.get('schedule_rule', '')}",
                user_id=user_id,
                metadata={"category": "ROUTINE", "active": True}
            )

    def get_or_create_app_collection(self, app_name: str, tenant_id: str = "tenant_default"):
        """Returns or initializes a ChromaDB collection dedicated to a specific app for a specific tenant."""
        safe_tenant = _sanitize_collection_name(tenant_id)
        safe_app = _sanitize_collection_name(app_name)
        col_name = f"app_{safe_tenant}_{safe_app}"[:63]
        return self.client.get_or_create_collection(
            name=col_name,
            metadata={"app": app_name, "tenant": tenant_id, "type": "app_specific_trajectory_memory"}
        )

    def add_app_memory(self, app_name: str, doc_id: str, text: str, metadata: Dict[str, Any] = None, tenant_id: str = "tenant_default"):
        col = self.get_or_create_app_collection(app_name, tenant_id)
        meta = metadata or {}
        cleaned_meta = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v for k, v in meta.items()}
        col.upsert(ids=[doc_id], documents=[text], metadatas=[cleaned_meta])

    def search_app_memory(self, app_name: str, query: str, n_results: int = 3, tenant_id: str = "tenant_default") -> List[Dict[str, Any]]:
        col = self.get_or_create_app_collection(app_name, tenant_id)
        total = col.count()
        if total == 0:
            return []
        limit = min(n_results, total)
        try:
            results = col.query(query_texts=[query], n_results=limit)
        except Exception:
            return []

        matches = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
            for doc, meta, dist in zip(docs, metas, distances):
                similarity = round(max(0, 1.0 - (dist / 2.0)) * 100, 1)
                matches.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": round(dist, 3),
                    "similarity": f"{similarity}%",
                    "app": app_name
                })
        return matches


# Global instance
vector_memory = VectorMemoryStore()
