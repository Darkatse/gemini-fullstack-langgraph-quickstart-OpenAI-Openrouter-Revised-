from datetime import datetime


# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


query_writer_instructions = """Your goal is to generate sophisticated and diverse web search queries. These queries are intended for an advanced automated web research tool capable of analyzing complex results, following links, and synthesizing information.

Instructions:
- Always prefer a single search query, only add another query if the original question requests multiple aspects or elements and one query is not enough.
- Each query should focus on one specific aspect of the original question.
- Don't produce more than {number_queries} queries.
- Queries should be diverse, if the topic is broad, generate more than 1 query.
- Don't generate multiple similar queries, 1 is enough.
- Query should ensure that the most current information is gathered. The current date is {current_date}.

Format: 
- Format your response as a JSON object with ALL three of these exact keys:
   - "rationale": Brief explanation of why these queries are relevant
   - "query": A list of search queries

Example:

Topic: What revenue grew more last year apple stock or the number of people buying an iphone
```json
{{
    "rationale": "To answer this comparative growth question accurately, we need specific data points on Apple's stock performance and iPhone sales metrics. These queries target the precise financial information needed: company revenue trends, product-specific unit sales figures, and stock price movement over the same fiscal period for direct comparison.",
    "query": ["Apple total revenue growth fiscal year 2024", "iPhone unit sales growth fiscal year 2024", "Apple stock price growth fiscal year 2024"],
}}
```

Context: {research_topic}"""


web_searcher_instructions = """Conduct targeted Google Searches to gather the most recent, credible information on "{research_topic}" and synthesize it into a verifiable text artifact.

Instructions:
- Query should ensure that the most current information is gathered. The current date is {current_date}.
- Conduct multiple, diverse searches to gather comprehensive information.
- Consolidate key findings while meticulously tracking the source(s) for each specific piece of information.
- The output should be a well-written summary or report based on your search findings. 
- Only include the information found in the search results, don't make up any information.

Research Topic:
{research_topic}
"""

reflection_instructions = """You are an expert research assistant analyzing summaries about "{research_topic}".

Instructions:
- Analyze the following summaries, which are derived from web searches.
- Each summary is formatted as: "Source [number]: Title\nURL: url\nContent: snippet".
- Based on these summaries, determine if you have sufficient information to provide a comprehensive answer to the user's original question: "{research_topic}".
- If the information is insufficient, identify the knowledge gaps and generate specific, targeted follow-up queries for a web search tool.
- If the information is sufficient, state that and provide an empty list for follow-up queries.

Requirements:
- Ensure any follow-up queries are self-contained and provide enough context.

Output Format:
- Format your response as a JSON object with these exact keys:
   - "is_sufficient": true or false
   - "knowledge_gap": A string describing what information is missing. If sufficient, this should be an empty string.
   - "follow_up_queries": A list of strings, where each string is a follow-up search query. If sufficient, this should be an empty list.

Example:
```json
{{
    "is_sufficient": false,
    "knowledge_gap": "The summaries confirm the event happened but lack details on the specific individuals who won awards.",
    "follow_up_queries": ["Who won the Best Player award at Euro 2024?", "Who was the top goal scorer at Euro 2024?"]
}}
```

Reflect carefully on the Summaries to identify knowledge gaps and produce a follow-up query. Then, produce your output following this JSON format:

Summaries:
{summaries}
"""

answer_instructions = """You are a research assistant. Your task is to generate a high-quality, comprehensive answer to the user's question based on the provided web search summaries.

Instructions:
- The current date is {current_date}.
- You are the final step of a multi-step research process, don't mention that you are the final step. 
- You have access to all the information gathered from the previous steps.
- You have access to the user's question.
- Generate a high-quality answer to the user's question based on the provided summaries and the user's question.
- you MUST include all the citations from the summaries in the answer correctly.

User Context:
- {research_topic}

Summaries:
{summaries}"""
