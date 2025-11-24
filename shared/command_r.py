"""Command R - command understanding model for Osiris.

Turns natural language instructions into concrete shell commands
or helpful explanations. Uses simple patterns first, then falls
back to a local LLM via Ollama (phi3:mini) if available.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

import requests

from shared.rag_index import build_osiris_index


@dataclass
class CommandSuggestion:
    """Represents Command R's suggestion for what to do."""
    command: str
    explanation: str
    confidence: float


class CommandRModel:
    """Simple model for interpreting natural language commands."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

        # Tiny in-memory examples you can extend.
        self.examples = [
            {
                "patterns": ["make a folder", "create a folder", "new folder"],
                "template": "mkdir {name}",
                "default_name": "new_folder",
                "explanation": "Creates a new directory.",
            },
            {
                "patterns": ["list files", "show files", "show directory", "show folders"],
                "command": "ls",
                "explanation": "Lists files and directories in the current folder.",
            },
            {
                "patterns": ["where am i", "current directory", "show current directory"],
                "command": "pwd",
                "explanation": "Shows the current working directory.",
            },
            {
                "patterns": ["delete folder", "remove folder"],
                "template": "rm {name}",
                "default_name": "folder_to_delete",
                "explanation": "Deletes a folder or file.",
            },
        ]

        self.docs = self._load_docs()

        # Optional RAG index over docs (Chroma + llama-index)
        self.index = None
        try:
            self.index = build_osiris_index()
        except Exception:
            self.index = None

    def _load_docs(self) -> List[str]:
        """Load local docs (currently unused, for future RAG)."""
        root = Path(__file__).parent.parent
        patterns = [
            root / "iris_cli_framework" / "COMPONENT_EXPLANATION.md",
            root / "shiv_command_execution" / "COMPONENT_EXPLANATION.md",
            root / "kshitij_safety_gate" / "COMPONENT_EXPLANATION.md",
            root / "prabal_efficiency_metrics" / "COMPONENT_EXPLANATION.md",
        ]

        docs: List[str] = []
        for path in patterns:
            if path.exists():
                try:
                    docs.append(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return docs

    def suggest(self, instruction: str) -> Optional[CommandSuggestion]:
        """Suggest a shell command for a natural language instruction."""
        if not self.enabled:
            return None

        text = instruction.strip().lower()
        if not text:
            return None

        # 1) Try simple patterns
        suggestion = self._pattern_match(text)
        if suggestion is not None:
            return suggestion

        # 2) Fallback to local LLM (Ollama phi3:mini)
        return self._rag_suggest(text)

    def _pattern_match(self, text: str) -> Optional[CommandSuggestion]:
        """Cheap pattern-based matcher over examples."""
        for example in self.examples:
            for pat in example["patterns"]:
                if text.startswith(pat):
                    if "template" in example:
                        name = self._extract_name(
                            text,
                            prefix=pat,
                            default=example.get("default_name", "item"),
                        )
                        cmd = example["template"].format(name=name)
                    else:
                        cmd = example["command"]

                    return CommandSuggestion(
                        command=cmd,
                        explanation=example.get("explanation", ""),
                        confidence=0.8,
                    )
        return None

    def _extract_name(self, text: str, prefix: str, default: str) -> str:
        """Extract a single name token after a given prefix."""
        rest = text[len(prefix):].strip()
        if not rest:
            return default
        return rest.split()[0]

    def _rag_suggest(self, text: str) -> Optional[CommandSuggestion]:
        """Use local Ollama (phi3:mini) to propose a command.

        If a RAG index is available, include retrieved context from the
        project documentation in the prompt so the model has more
        information about how Osiris works.
        """

        model_name = self.config.get("llm_model", "phi3:mini")
        url = self.config.get("llm_endpoint", "http://localhost:11434/api/chat")

        # Retrieve a bit of context from the RAG index, if available
        context_snippets = ""
        if getattr(self, "index", None) is not None:
            try:
                query_engine = self.index.as_query_engine(similarity_top_k=3)
                result = query_engine.query(text)
                context_snippets = str(result)
            except Exception:
                context_snippets = ""

        allowed_commands = """
- pwd               # show current directory
- ls                # list files
- mkdir <name>      # create folder
- rm <name>         # delete file or folder
- cat <file>        # show file contents
""".strip()

        prompt = f"""
You are Command R, an operating system assistant that turns messy
natural language into safe shell commands.

Relevant context from the OS documentation (may be empty):
{context_snippets}

User request: {text}

You MUST:
- Choose ONE command that best matches the user's intent.
- The command must be one of the allowed primitives, possibly
  with arguments filled in:
{allowed_commands}
- If you are not sure, choose the safest reasonable command.
- Respond with ONLY a JSON object on a single line, like:
  {{"command": "pwd", "explanation": "Shows the current directory"}}
""".strip()

        try:
            data = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Command R, a shell command generator that ONLY outputs JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }

            resp = requests.post(url, json=data, timeout=30)
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "").strip()

            first_brace = content.find("{")
            last_brace = content.rfind("}")
            if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
                return None

            json_str = content[first_brace:last_brace + 1]
            obj = json.loads(json_str)

            cmd = obj.get("command")
            expl = obj.get("explanation", "")
            if not cmd or not isinstance(cmd, str):
                return None

            return CommandSuggestion(
                command=cmd,
                explanation=expl,
                confidence=0.7,
            )
        except Exception:
            return None


__all__ = ["CommandRModel", "CommandSuggestion"]