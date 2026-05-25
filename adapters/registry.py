from .types import AgentInfo
from . import claude, codex


def detect_agents() -> list[AgentInfo]:
    agents: list[AgentInfo] = []
    for detector in [codex.detect, claude.detect]:
        info = detector()
        if info:
            agents.append(info)
    return agents
