import os
import re

agent_dir = "/Users/shreedshrivastava/Projects/Archon.AI/src/archon/agents"

for filename in os.listdir(agent_dir):
    if not filename.endswith(".py"):
        continue

    filepath = os.path.join(agent_dir, filename)
    with open(filepath, "r") as f:
        content = f.read()

    content = content.replace(
        "async def execute(self, task: Task, model: ModelType) -> TaskResult:",
        "async def execute(self, task: Task, model: ModelType, project_memory=None) -> TaskResult:",
    )

    pattern = r"([ \t]+)response = await self\._call_model\(model, prompt\)"

    if "if project_memory:" not in content:
        replacement = r'\1if project_memory:\n\1    prompt += f"\\n\\nProject Memory Summary:\\n{project_memory.model_dump_json(indent=2)}\\n"\n\1response = await self._call_model(model, prompt)'
        content = re.sub(pattern, replacement, content)

    with open(filepath, "w") as f:
        f.write(content)

print("Agent refactor completed.")
