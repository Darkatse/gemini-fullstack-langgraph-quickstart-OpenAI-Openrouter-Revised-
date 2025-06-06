# backend/src/agent/graph.py

import os
import json
from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    reflection_instructions,
    answer_instructions,
)
from agent.utils import get_research_topic

load_dotenv()

if os.getenv("OPENROUTER_API_KEY") is None:
    raise ValueError("OPENROUTER_API_KEY is not set")
if os.getenv("TAVILY_API_KEY") is None:
    raise ValueError("TAVILY_API_KEY is not set")

# 辅助函数：创建 OpenAI 兼容的 LLM 实例
def get_llm(configurable: Configuration, model_name: str) -> ChatOpenAI:
    """
    创建一个配置为使用 OpenRouter 的 ChatOpenAI 实例。
    """
    return ChatOpenAI(
        model=model_name,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",  # 根据 OpenRouter 要求
            "X-Title": "Gemini Fullstack LangGraph",  # 根据 OpenRouter 要求
        },
    )

# --- Nodes ---

def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """
    LangGraph 节点，根据用户的问题生成搜索查询。
    使用配置的 LLM（通过 OpenRouter）为网络研究创建优化的搜索查询。
    """
    configurable = Configuration.from_runnable_config(config)

    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    llm = get_llm(configurable, configurable.query_generator_model)
    structured_llm = llm.with_structured_output(SearchQueryList)

    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    )
    
    print("--- Generating Search Queries ---")
    result = structured_llm.invoke(formatted_prompt)
    print(f"--- Generated Queries: {result.query} ---")
    
    return {"query_list": result.query}


def continue_to_web_research(state: QueryGenerationState):
    """
    LangGraph 节点，将搜索查询分发到 web_research 节点。
    这用于为每个搜索查询并行生成一个 web_research 节点的任务。
    """
    return [
        Send("web_research", {"search_query": search_query})
        for search_query in state["query_list"]
    ]


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """
    LangGraph 节点，使用 Tavily API 执行网络搜索。
    """
    search_query = state["search_query"]
    print(f"--- Executing Tavily Search for: '{search_query}' ---")

    tavily_tool = TavilySearchResults(max_results=5, search_depth="advanced")
    search_results = tavily_tool.invoke({"query": search_query})

    # 将结果格式化为对 LLM 更友好的字符串
    formatted_results = ""
    for i, res in enumerate(search_results):
        formatted_results += f"Source [{i+1}]: {res['title']}\nURL: {res['url']}\nContent: {res['content']}\n\n"

    print(f"--- Tavily Search for '{search_query}' completed. ---")

    return {
        "web_research_result": [formatted_results],
        "sources_gathered": search_results,
        "search_query": [search_query],
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """
    LangGraph 节点，用于识别知识差距并生成潜在的后续查询。
    """
    configurable = Configuration.from_runnable_config(config)
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    
    model_name = state.get("reflection_model") or configurable.reflection_model
    llm = get_llm(configurable, model_name)
    structured_llm = llm.with_structured_output(Reflection)

    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )

    print("--- Reflecting on search results ---")
    result = structured_llm.invoke(formatted_prompt)
    print(f"--- Reflection result: Sufficient? {result.is_sufficient}, Gaps: {result.knowledge_gap} ---")
    
    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "research_loop_count": state["research_loop_count"],
    }


def evaluate_research(state: ReflectionState, config: RunnableConfig) -> str:
    """
    LangGraph 路由函数，决定研究流程的下一步。
    """
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )

    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        print("--- Research deemed sufficient. Finalizing answer. ---")
        return "finalize_answer"
    else:
        print("--- Research insufficient. Generating follow-up queries. ---")
        return [
            Send("web_research", {"search_query": follow_up_query})
            for follow_up_query in state["follow_up_queries"]
        ]


def finalize_answer(state: OverallState, config: RunnableConfig) -> dict:
    """
    LangGraph 节点，用于生成最终的研究答案。
    """
    configurable = Configuration.from_runnable_config(config)
    model_name = state.get("answer_model") or configurable.answer_model
    llm = get_llm(configurable, model_name)

    current_date = get_current_date()
    
    # 格式化原始来源列表以供 LLM 引用
    source_list = "\n".join(
        [
            f"[{i+1}]: [{source['title']}]({source['url']})"
            for i, source in enumerate(state["sources_gathered"])
        ]
    )

    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
        source_list=source_list
    )

    print("--- Finalizing answer ---")
    result = llm.invoke(formatted_prompt)

    return {
        "messages": [AIMessage(content=result.content)],
        "sources_gathered": state["sources_gathered"],
    }


# --- Graph Definition ---

builder = StateGraph(OverallState, config_schema=Configuration)

builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "generate_query")

builder.add_conditional_edges(
    "generate_query",
    continue_to_web_research,
    ["web_research"]
)

builder.add_edge("web_research", "reflection")

builder.add_conditional_edges(
    "reflection",
    evaluate_research,
    {
        "web_research": "web_research",
        "finalize_answer": "finalize_answer"
    }
)

builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent-openrouter-tavily")