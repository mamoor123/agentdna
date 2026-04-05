# AgentDNA Framework Plugins

"""
Drop-in integrations for popular agent frameworks.

Supported:
- langchain: LangChain/LangGraph agent wrapper
- crewai: CrewAI crew wrapper
- raw: Raw OpenAI/Anthropic function-calling wrapper

Usage (LangChain):
    from agentdna.plugins.langchain import AgentDNAWrapper
    wrapped = AgentDNAWrapper(my_chain)
    # Your chain now auto-registers with AgentDNA and discovers other agents

Usage (CrewAI):
    from agentdna.plugins.crewai import AgentDNACrew
    crew = AgentDNACrew(agents=[...], tasks=[...])
    # Your crew can now discover and hire other agents from the registry
"""
