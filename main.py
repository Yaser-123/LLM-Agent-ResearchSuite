from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.prebuilt import create_react_agent
from tools import save_tool, search_tool, wiki_tool

import os

load_dotenv()

# Define the output schema
class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

# Use Gemini 2.5 Flash
llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

# Create parser for structured output
parser = PydanticOutputParser(pydantic_object=ResearchResponse)

# Prompt with format instructions for the parser
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a research assistant that will help generate a research paper.
            Answer the user query and use necessary tools.
            Wrap the output in this format and provide no other text:\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

# Register tools
tools = [search_tool, wiki_tool, save_tool]

# Create Gemini agent with tools using langgraph
agent_executor = create_react_agent(llm, tools)

# Take user input and run
query = input("What can I help you research? ")
raw_response = agent_executor.invoke({"messages": [("user", query)]})

# Try to parse and display result
import json
import re

try:
    # Extract output from langgraph response
    output_text = raw_response["messages"][-1].content

    if isinstance(output_text, list):
        output_text = output_text[0].get("text")

    match = re.search(r"```json\s*(\{.*?\})\s*```", output_text, re.DOTALL)
    if match:
        json_data = json.loads(match.group(1))
    else:
        json_data = json.loads(output_text)

    structured_response = ResearchResponse(**json_data)
    print("\n✅ Structured Response:\n", structured_response)

    # Save using the actual tool function
    save_message = save_tool.func(structured_response.summary)
    print("\n📁", save_message)

except Exception as e:
    print("❌ Error parsing response:", e)
    print("🔎 Raw Response -", raw_response)

