"""
Filesystem Writer Module.

Responsible for safely committing agent-generated files to the project directory.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class FileWriter:
    """
    Safely writes generated artifacts to the local filesystem.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        from archon.intelligence.code_retriever import CodeRetriever
        from archon.manager.patch_applier import PatchApplier

        self.code_retriever = CodeRetriever(str(self.project_path))
        self.patch_applier = PatchApplier(str(self.project_path))

    def write_artifacts(
        self,
        result: Any,
        agent: str = "UnknownAgent",
        ownership_map: Optional[Dict[str, str]] = None,
        project_memory: Optional[Any] = None,
    ) -> List[str]:
        """
        Extracts files from TaskResult and writes them to disk.
        Checks ownership map to prevent overwrites.
        Returns a list of created file paths (relative to project).
        """
        created_files = []
        if ownership_map is None:
            ownership_map = {}

        # Determine if result is a TaskResult object or a raw dict
        output = getattr(result, "output", result)

        files_to_write = []

        if isinstance(output, dict):
            # 1. Process explicit patches first
            if "patches" in output:
                for patch_data in output["patches"]:
                    fpath = patch_data.get("file")
                    patch_instructions = patch_data.get("patch", [])
                    fallback_content = patch_data.get("content")

                    if not fpath or not patch_instructions:
                        continue

                    patched_content = self.patch_applier.apply_patch(fpath, patch_instructions)
                    if patched_content is not None:
                        files_to_write.append({"path": fpath, "content": patched_content})
                    else:
                        logger.warning(
                            f"Patch failed for {fpath}. Falling back to full file replacement."
                        )
                        if fallback_content:
                            files_to_write.append({"path": fpath, "content": fallback_content})
                        else:
                            logger.error(f"No fallback content provided for {fpath}.")

            # 2. Process regular files
            if "files" in output:
                for f in output["files"]:
                    files_to_write.append({"path": f.get("path"), "content": f.get("content", "")})

        elif isinstance(output, list):
            # Try to see if output itself is a list of file dicts
            for item in output:
                if isinstance(item, dict) and "path" in item and "content" in item:
                    files_to_write.append(
                        {"path": item.get("path"), "content": item.get("content", "")}
                    )

        # Write extracted files safely
        for file_data in files_to_write:
            rel_path = file_data.get("path")
            content = file_data.get("content")

            if not rel_path or content is None:
                continue

            try:
                # Resolve the path and ensure it's within project_path
                target_path = (self.project_path / rel_path).resolve()

                # Prevent path traversal outside project workspace
                if not str(target_path).startswith(str(self.project_path)):
                    logger.warning(f"Path traversal detected and blocked: {rel_path}")
                    continue

                # Format relative path for logging
                # This should look like "backend/app.js"
                rel_str = str(target_path.relative_to(self.project_path))

                # Check file ownership map
                if rel_str in ownership_map:
                    owner = ownership_map[rel_str]
                    if owner != agent:
                        logger.warning(
                            f"Conflict detected on {rel_str}. Owned by: {owner}, attempted modification by: {agent}."
                        )
                        if hasattr(result, "file_conflicts"):
                            # Read original content
                            try:
                                with open(target_path, "r", encoding="utf-8") as rf:
                                    original_content = rf.read()
                            except Exception:
                                original_content = ""

                            result.file_conflicts.append(
                                {
                                    "path": rel_str,
                                    "owner": owner,
                                    "attempted_by": agent,
                                    "original_content": original_content,
                                    "attempted_content": content,
                                    "target_path": target_path,
                                }
                            )
                        # Prevent overwrite, let orchestrator handle it via Arbitrator
                        continue
                else:
                    ownership_map[rel_str] = agent

                # Create directories if they do not exist
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Write file content to the correct path
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)

                if project_memory and hasattr(project_memory, "codebase_index"):
                    project_memory.codebase_index.update_from_file(rel_str, content)

                if hasattr(self, "code_retriever"):
                    self.code_retriever.embed_file(rel_str, content)

                created_files.append(rel_str)
                logger.info(f"Successfully wrote file: {rel_str}")
                # Log explicitly per requirements
                print(f"📝 Created {rel_str} (owner: {agent})")

            except Exception as e:
                logger.error(f"Failed to write file {rel_path}: {e}")

        return created_files
