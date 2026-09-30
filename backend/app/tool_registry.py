"""
Decorator-Based Tool Registry for Synapse AI Agent
Inspired by Qwen-Agent @register_tool and minitap-ai atomic tool primitives.
Provides dynamic registration, JSON schema generation, risk classification,
and reflection-ready execution contracts.
"""

import inspect
import importlib
import pkgutil
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Callable

class BaseTool(ABC):
    """Abstract base class for all Synapse Agent Tools."""
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    risk_level: str = "low"  # low, medium, high, critical
    category: str = "device" # device, service, intelligence, system

    def to_schema(self) -> Dict[str, Any]:
        """Returns JSON schema representation compatible with OpenAI/Qwen tool calls."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
                "risk_level": self.risk_level,
                "category": self.category
            }
        }

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool logic and return structured result."""
        pass


class ToolRegistryEngine:
    """Singleton registry holding all instantiated agent tools."""
    _instance = None
    _registry: Dict[str, BaseTool] = {}
    _classes: Dict[str, Type[BaseTool]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistryEngine, cls).__new__(cls)
            cls._instance._registry = {}
            cls._instance._classes = {}
        return cls._instance

    def register(self, cls_or_name=None, name: Optional[str] = None, risk_level: str = "low", category: str = "device", description: str = ""):
        """
        Decorator to register a tool class.
        Can be used as:
          @register_tool
          @register_tool("custom_name")
          @register_tool(name="custom_name", risk_level="medium")
        """
        chosen_name = name or (cls_or_name if isinstance(cls_or_name, str) else None)

        def decorator(tool_cls: Type[BaseTool]):
            n = chosen_name or getattr(tool_cls, "name", None) or tool_cls.__name__
            tool_cls.name = n
            if risk_level:
                tool_cls.risk_level = risk_level
            if category:
                tool_cls.category = category
            if description:
                tool_cls.description = description

            instance = tool_cls()
            self._classes[n] = tool_cls
            self._registry[n] = instance
            return tool_cls

        if inspect.isclass(cls_or_name) and issubclass(cls_or_name, BaseTool):
            tool_cls = cls_or_name
            n = chosen_name or getattr(tool_cls, "name", None) or tool_cls.__name__
            self._classes[n] = tool_cls
            self._registry[n] = tool_cls()
            return tool_cls

        return decorator

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._registry.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_schema() for tool in self._registry.values()]

    def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' not found in registry",
                "available_tools": list(self._registry.keys())
            }
        try:
            res = tool.execute(params)
            if isinstance(res, dict):
                if "success" not in res:
                    res["success"] = True
                return res
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e), "tool": name}

    def discover(self, package_path="app.tools"):
        """Auto-discovers and imports all tool classes in the tools package."""
        try:
            pkg = importlib.import_module(package_path)
            if hasattr(pkg, "__path__"):
                for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
                    importlib.import_module(f"{package_path}.{module_name}")
        except Exception as e:
            print(f"Tool auto-discovery notice: {e}")


# Singleton instance
tool_registry = ToolRegistryEngine()
register_tool = tool_registry.register

def get_tool(name: str) -> Optional[BaseTool]:
    return tool_registry.get_tool(name)

def list_registered_tools() -> List[Dict[str, Any]]:
    return tool_registry.list_tools()

def execute_tool(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return tool_registry.execute(name, params)
