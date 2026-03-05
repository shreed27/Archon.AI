import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class PatchApplier:
    """
    Applies structured patches to existing files on disk.
    If the patch fails, it throws an error or explicitly falls back.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()

    def apply_patch(self, file_path: str, patches: List[Dict[str, str]]) -> Optional[str]:
        """
        Applies a list of patch instructions to the content of file_path.
        Returns the new content, or None if the patch cannot be safely applied.
        """
        target_path = (self.project_path / file_path).resolve()

        # Verify ownership / bounds
        if not str(target_path).startswith(str(self.project_path)):
            logger.warning(f"Path traversal detected and blocked: {file_path}")
            return None

        if not target_path.exists():
            logger.warning(f"File {file_path} does not exist. Cannot apply patch.")
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()

            for p in patches:
                p_type = p.get("type")
                if p_type == "insert":
                    after_str = p.get("after")
                    insert_content = p.get("content", "")
                    if after_str and after_str in content:
                        # Append the content immediately after the "after" block
                        # we could also handle trailing newlines gracefully
                        content = content.replace(after_str, f"{after_str}\n{insert_content}")
                    else:
                        logger.error(f"Patch insert failed, target string not found: '{after_str}'")
                        return None

                elif p_type == "replace":
                    target = p.get("target")
                    replace_content = p.get("content", "")
                    if target and target in content:
                        content = content.replace(target, replace_content)
                    else:
                        logger.error(f"Patch replace failed, target string not found: '{target}'")
                        return None

                elif p_type == "delete":
                    target = p.get("target")
                    if target and target in content:
                        content = content.replace(target, "")
                    else:
                        logger.error(f"Patch delete failed, target string not found: '{target}'")
                        return None
                else:
                    logger.warning(f"Unknown patch type '{p_type}'")

            return content
        except Exception as e:
            logger.error(f"Failed to apply patch to {file_path}: {e}")
            return None
