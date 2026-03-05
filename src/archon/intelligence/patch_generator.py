import os
from typing import List, Dict, Any, Optional
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class PatchGenerator:
    """
    Helps agents generate patches instead of full file replacements.
    Formats prompts or agent contexts to instruct the model to return targeted edits.
    """

    @staticmethod
    def get_patch_prompt_instructions() -> str:
        """
        Returns instructions to append to the agent prompt when modifying existing code.
        """
        return """
When modifying EXISTING files, you MUST use the patch format instead of rewriting the entire file.
Fallback to full file replacement ONLY if the file is new or the changes are too complex for a simple patch.

Example Patch Format:
{
    "patches": [
        {
            "file": "backend/server.js",
            "patch": [
                {
                    "type": "insert",
                    "after": "app.use('/users', userRoutes);",
                    "content": "const authRoutes = require('./routes/auth');\\napp.use('/auth', authRoutes);"
                },
                {
                    "type": "replace",
                    "target": "const PORT = 3000;",
                    "content": "const PORT = process.env.PORT || 3000;"
                },
                {
                    "type": "delete",
                    "target": "console.log('test');"
                }
            ]
        }
    ]
}

Note:
- "target" or "after" string must exactly match a snippet in the file (even one line).
- Provide minimal, targeted edits.
"""
