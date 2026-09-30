"""
YAML Prompt Template System for Synapse AI Agent
Inspired by MadeAgents 16 modular YAML prompt templates.
Loads, validates, and renders externalized YAML prompts with variable interpolation.
"""

import os
import re
from typing import Dict, Any, List, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class PromptTemplate:
    """Represents a single parsed YAML prompt template."""
    def __init__(self, name: str, data: Dict[str, Any]):
        self.name = name
        self.description = data.get("description", "")
        self.system_prompt = data.get("system_prompt", "")
        self.user_prompt = data.get("user_prompt", "")
        self.variables = data.get("variables", [])
        self.metadata = data.get("metadata", {})

    def render(self, **kwargs) -> str:
        """Interpolates variables {var} in system_prompt and user_prompt."""
        text = self.system_prompt
        if self.user_prompt:
            text = f"{text}\n\n{self.user_prompt}" if text else self.user_prompt

        for k, v in kwargs.items():
            pattern = re.compile(r"\{" + re.escape(k) + r"\}")
            val_str = str(v) if v is not None else ""
            text = pattern.sub(val_str, text)
        return text

    def render_system(self, **kwargs) -> str:
        text = self.system_prompt
        for k, v in kwargs.items():
            pattern = re.compile(r"\{" + re.escape(k) + r"\}")
            val_str = str(v) if v is not None else ""
            text = pattern.sub(val_str, text)
        return text

    def render_user(self, **kwargs) -> str:
        text = self.user_prompt
        for k, v in kwargs.items():
            pattern = re.compile(r"\{" + re.escape(k) + r"\}")
            val_str = str(v) if v is not None else ""
            text = pattern.sub(val_str, text)
        return text


class PromptManager:
    """Manages prompt template loading, caching, and rendering."""
    _instance = None
    _templates: Dict[str, PromptTemplate] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._templates = {}
        return cls._instance

    def __init__(self, prompts_dir: Optional[str] = None):
        if not self._templates:
            if prompts_dir is None:
                # Find prompts directory relative to backend
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                prompts_dir = os.path.join(base, "prompts")
            self.prompts_dir = prompts_dir
            self.load_templates()

    def load_templates(self):
        """Scans and loads all .yaml and .yml files from prompts_dir."""
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir, exist_ok=True)
            return

        for fname in os.listdir(self.prompts_dir):
            if fname.endswith((".yaml", ".yml")):
                key = os.path.splitext(fname)[0]
                filepath = os.path.join(self.prompts_dir, fname)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    data = self._parse_yaml(content)
                    self._templates[key] = PromptTemplate(key, data)
                except Exception as e:
                    print(f"Error loading prompt template {fname}: {e}")

    def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """Parses YAML content using pyyaml or fallback block parser."""
        if HAS_YAML:
            return yaml.safe_load(content) or {}
        # Fallback simple parser if pyyaml ever unavailable
        res: Dict[str, Any] = {}
        curr_key = None
        curr_val = []
        is_block = False

        for line in content.splitlines():
            if ":" in line and not is_block:
                parts = line.split(":", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                if v == "|":
                    curr_key = k
                    curr_val = []
                    is_block = True
                else:
                    res[k] = v
            elif is_block:
                if line.startswith("  ") or not line.strip():
                    curr_val.append(line[2:] if line.startswith("  ") else line)
                else:
                    if curr_key:
                        res[curr_key] = "\n".join(curr_val)
                    is_block = False
                    if ":" in line:
                        parts = line.split(":", 1)
                        res[parts[0].strip()] = parts[1].strip()
        if curr_key and is_block:
            res[curr_key] = "\n".join(curr_val)
        return res

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        return self._templates.get(name)

    def render(self, name: str, **kwargs) -> str:
        tmpl = self.get_template(name)
        if not tmpl:
            return kwargs.get("fallback", f"[Template '{name}' not found]")
        return tmpl.render(**kwargs)

    def list_templates(self) -> List[str]:
        return sorted(list(self._templates.keys()))

    def reload(self):
        self._templates.clear()
        self.load_templates()


# Singleton instance
prompt_manager = PromptManager()

def render_prompt(template_name: str, **kwargs) -> str:
    return prompt_manager.render(template_name, **kwargs)
