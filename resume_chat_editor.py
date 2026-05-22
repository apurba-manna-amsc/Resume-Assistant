"""Parses chat messages into resume update commands and applies them."""

import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app_errors import ChatUpdateError
from groq_client import GroqClient
from groq_resume_service import FALLBACK_MODEL_ID

logger = logging.getLogger(__name__)


class ResumeChatEditor:
    """Turns natural-language chat into Python commands that mutate resume JSON."""

    def __init__(self, groq_client: GroqClient, model_id: str) -> None:
        self.client = groq_client
        self.llm_model = model_id

    def set_model(self, model_id: str) -> None:
        self.llm_model = model_id

    def parse_chat_request_to_commands(
        self, resume_json: Dict[str, Any], user_request: str
    ) -> List[str]:
        """Ask Groq for a Python list of resume mutation commands."""
        if not user_request.strip():
            return []

        resume_context = json.dumps(resume_json, indent=2)
        prompt = f"""
Parse this resume update request into Python commands that modify `resume` (a dict).

**CURRENT RESUME:**
```json
{resume_context}
```

**REQUEST:** {user_request}

Return ONLY a Python list of strings, e.g. ["resume['skills'].append('Python')"].
Use single quotes. No markdown. Empty list [] if unclear.
"""

        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only a valid Python list of command strings.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }

        commands_str = self.client.chat_completion(
            payload, max_retries=3, fallback_model=FALLBACK_MODEL_ID
        )
        commands_str = self.extract_command_list_from_llm_response(commands_str)
        commands = self._parse_command_list_string(commands_str)

        if not isinstance(commands, list) or not all(isinstance(c, str) for c in commands):
            logger.warning("Invalid command list from LLM: %s", commands_str[:200])
            return []

        return commands

    def _parse_command_list_string(self, commands_str: str) -> List[str]:
        if not (commands_str.startswith("[") and commands_str.endswith("]")):
            return []
        try:
            return ast.literal_eval(commands_str)
        except (ValueError, SyntaxError):
            logger.warning("AST parse failed for commands: %s", commands_str[:200])
            return []

    def extract_command_list_from_llm_response(self, response_text: str) -> str:
        """Extract a Python list of command strings from the Groq response."""
        response_text = re.sub(r"```python\n?", "", response_text)
        response_text = re.sub(r"```\n?", "", response_text).strip()

        if response_text.startswith("["):
            bracket_count = 0
            for i, char in enumerate(response_text):
                if char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        return response_text[: i + 1]

        matches = re.findall(r"\[.*?\]", response_text, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()
        return "[]"

    def apply_update_commands_to_resume(
        self, resume_json: Dict[str, Any], commands: List[str]
    ) -> Dict[str, Any]:
        """Execute update commands; raises if every command fails."""
        if not commands:
            return resume_json

        resume = resume_json
        failures: List[str] = []
        executed = 0

        for command in commands:
            try:
                exec(command, {"__builtins__": {}}, {"resume": resume})
                executed += 1
                logger.info("Executed chat command: %s", command)
            except Exception as exc:
                logger.warning("Chat command failed: %s — %s", command, exc)
                failures.append(command[:80])

        if executed == 0:
            raise ChatUpdateError(
                "None of the suggested updates could be applied. "
                "Try rephrasing your request (e.g. 'Add Python to my skills').",
                detail="; ".join(failures),
            )

        return resume
