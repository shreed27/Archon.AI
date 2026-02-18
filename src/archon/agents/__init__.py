"""
ARCHON Agents package.

Importing this package registers all agents with the agent registry.
Use get_agent(AgentType) to retrieve an agent instance.
"""

from archon.agents.base_agent import BaseAgent, get_agent, register_agent

# Import all agents to trigger their register_agent() calls
from archon.agents.backend_agent import BackendAgent
from archon.agents.frontend_agent import FrontendAgent
from archon.agents.devops_agent import DevOpsAgent
from archon.agents.security_agent import SecurityAgent
from archon.agents.testing_agent import TestingAgent
from archon.agents.integration_agent import IntegrationAgent
from archon.agents.documentation_agent import DocumentationAgent
from archon.agents.git_agent import GitAgent

__all__ = [
    "BaseAgent",
    "get_agent",
    "register_agent",
    "BackendAgent",
    "FrontendAgent",
    "DevOpsAgent",
    "SecurityAgent",
    "TestingAgent",
    "IntegrationAgent",
    "DocumentationAgent",
    "GitAgent",
]
