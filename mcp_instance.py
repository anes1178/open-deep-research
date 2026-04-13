지금 내 코드는

from typing import Annotated
from fastmcp import Context
from pydantic import Field
from mcp_instance import mcp

from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from langchain_core.runnables import RunnableConfig
from sub_agent.requirement_agent.deep_code_research.configuration import DeepCodeSearchConfiguration, MCPConfig
from sub_agent.requirement_agent.deep_code_research.deep_researcher import deep_researcher, researcher_subgraph
import time
import json

##config
configuration = DeepCodeSearchConfiguration()
configurable_dict = configuration.model_dump()
configurable_dict['mcp_config'] = MCPConfig(
    url="http://fetch-mcp.kspprd.dks.cloud.samsungds.net/",
    tools=["read_confluence", "read_github_repo"],
    auth_required=True,
    headers= {
        "github-token": os.environ["GITHUB_TOKEN"],
        "confluence-username": os.environ["CONFLUENCE_USERNAME"],
        "confluence-password": os.environ["CONFLUENCE_PASSWORD"]
    }
)
configurable_dict["mcp_prompt"] = """
IMPORTANT: These tools can ONLY be used when an explicit link is provided in the user's message.

2. **read_github_repo**:
   - Purpose: Analyze internal repositories hosted on github.samsungds.net.
   - ⚠️ LIMITATION: This tool CANNOT read an entire repository.
   - ⚠️ It can ONLY read a specific file URL (e.g., a direct link to README.md or src/main.py).
   - It CANNOT:
        • list repository contents
        • traverse directories
        • recursively analyze a repo
        • read multiple files automatically
   - You MUST ONLY call this tool if the user explicitly provides:
        • a github.samsungds.net URL
        • OR a //go/... link that refers to internal documentation
   - If no GitHub link is present, DO NOT call this tool.

3. **read_confluence**:
   - Purpose: Analyze internal documentation hosted on confluence.samsungds.net.
   - You MUST ONLY call this tool if the user explicitly provides:
        • a confluence.samsungds.net link
        • OR a //go/... link that refers to internal documentation
   - If no Confluence link is present, DO NOT call this tool.

Strict Tool Usage Rules:
- Do NOT infer or guess internal links.
- Do NOT call these tools without an explicit URL in the user message.
- If a valid link is present, call the corresponding tool.
- If no link is present, continue reasoning without MCP tools.
"""
config = RunnableConfig(
    configurable=configurable_dict
)

async def run_requirement_agent(query):
    start_time = time.time()
    final_state = await researcher_subgraph.ainvoke(
        {"researcher_messages": [{"role": "user", "content": query},],
         "research_topic": query
         },
        config
    )
    end_time = time.time()
    elapsed = end_time - start_time
    print("🚀final_state",elapsed)
    
    with open("responses2.txt", "w", encoding="utf-8") as f:
        data = final_state['compressed_research'] + "시간: ", elapsed
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    return final_state['compressed_research']


@mcp.tool(
        name = "requirement_sub_agent",
        description = """
Use this agent when a user presents a new feature request, project brief, user story, bug report, or any ambiguous description of what needs to be built or changed. This agent should be invoked to structure and clarify requirements before development begins.\n\n<example>\nContext: The user describes a vague feature they want added to the open_deep_research project.\nuser: "I want the research agent to be smarter about finding sources and maybe cache things so it doesn't repeat searches."\nassistant: "Let me use the requirements-analyst agent to break down and structure these requirements properly."\n<commentary>\nThe user's request is vague and contains multiple implicit requirements. Launch the requirements-analyst agent to extract, clarify, and organize these into well-defined requirements.\n</commentary>\n</example>\n\n<example>\nContext: A product manager provides a high-level project description for a new capability in open_deep_research.\nuser: "We need to add support for PDF uploads so users can do research based on their own documents alongside web search."\nassistant: "I'll invoke the requirements-analyst agent to analyze and structure these requirements into a clear specification."\n<commentary>\nThis is a new feature request that needs to be broken down into functional and non-functional requirements, edge cases, and acceptance criteria. Use the requirements-analyst agent.\n</commentary>\n</example>\n\n<example>\nContext: A developer asks what needs to be done to improve the configuration system in the project.\nuser: "The configuration.py feels messy. Can you figure out what we need to do to clean it up?"\nassistant: "I'll use the requirements-analyst agent to analyze the current state and define clear improvement requirements."\n<commentary>\nThis is a refactoring request that needs structured analysis. The requirements-analyst agent will identify pain points, constraints, and success criteria.\n</commentary>\n</example>
        """
)

async def requirement_sub_agent(
    context: Context, 
    query: Annotated[
        str,
        Field(
            description="""
            A request or question based on the Confluence page content.
            Detect the user's language automatically (e.g., Korean, English)
            and use the same language in the query.
            If the user wrote in Korean, keep the query in Korean.
            If the user wrote in English, keep the query in English.
            """
            )
        ]
    ):
    
    result = await run_requirement_agent(query)
    return result