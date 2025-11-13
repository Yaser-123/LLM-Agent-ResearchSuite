import streamlit as st
from dotenv import load_dotenv
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tools import wiki_tool, search_tool, save_tool
from langgraph.prebuilt import create_react_agent
from datetime import datetime

load_dotenv()

# --- Pydantic model for structured output ---
class ResearchResponse(BaseModel):
    topic: str
    exploration: str
    summary: list[str]
    sources: list[str]
    tools_used: list[str]

# --- Tool options ---
tools = {
    "Wikipedia": wiki_tool,
    "Web Search": search_tool,
    "Save to File": save_tool,
}

# --- Streamlit UI ---
st.title("📚 AI Research Assistant")
st.markdown("""
Welcome to the AI-powered research assistant! Choose your tools, ask a question, and get a structured summary.
""")

query = st.text_input("🔍 What would you like to research?")
selected_tools = st.multiselect("🛠 Select Tools to Use", list(tools.keys()), default=["Wikipedia", "Web Search"])
llm_choice = st.selectbox("🧠 Choose LLM", ["Gemini 2.5", "Claude 3.5", "GPT-4"])
run_button = st.button("Run Research")

if run_button and query:
    with st.spinner("Running research agent..."):

        # Select LLM
        if llm_choice == "Gemini 2.5":
            llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
        elif llm_choice == "Claude 3.5":
            llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
        else:
            llm = ChatOpenAI(model="gpt-4")

        parser = PydanticOutputParser(pydantic_object=ResearchResponse)

        selected_tool_instances = [tools[t] for t in selected_tools if t != "Save to File"]
        
        st.write(f"🛠️ Tools available: {[t.name for t in selected_tool_instances]}")
        
        # Test tools directly
        st.write("Testing Wikipedia tool...")
        try:
            wiki_result = wiki_tool.func("Batman")
            st.success(f"✅ Wiki works: {wiki_result[:100]}...")
        except Exception as e:
            st.error(f"❌ Wiki failed: {e}")

        # Create agent using langgraph with higher recursion limit
        agent_executor = create_react_agent(llm, selected_tool_instances)
        
        # Configure with recursion limit
        config = {"recursion_limit": 10}

        # Direct approach: Call tools then LLM
        st.write("🔄 Gathering research...")
        
        # Step 1: Extract main topic from query for better Wikipedia search
        # If query asks for "facts about X", search for "X" directly
        search_query = query
        if "facts about" in query.lower() or "information about" in query.lower():
            # Extract the subject (e.g., "Batman" from "5 unknown facts about Batman")
            import re
            match = re.search(r'about\s+(.+?)(?:\s+in\s+short)?$', query, re.IGNORECASE)
            if match:
                search_query = match.group(1).strip()
        
        st.write(f"🔍 Searching Wikipedia for: {search_query}")
        wiki_info = wiki_tool.func(search_query)
        st.write(f"📚 Wikipedia result: {wiki_info[:200]}...")
        
        # Step 2: Ask LLM to format as JSON
        final_prompt = f"""You are a research assistant. Based on the Wikipedia information below, answer the user's query: "{query}"

Wikipedia Information:
{wiki_info}

Your task:
1. Extract or infer interesting facts/information that answer the query
2. Create a detailed exploration (2-3 paragraphs)
3. Provide 5 key summary points

Format your response as JSON:
{{
  "topic": "{query}",
  "exploration": "Write 2-3 detailed paragraphs explaining what you found",
  "summary": ["fact 1", "fact 2", "fact 3", "fact 4", "fact 5"],
  "sources": ["Wikipedia"],
  "tools_used": ["wikipedia_lookup"]
}}

Important: Use the Wikipedia info to CREATE the facts/points. Don't say "not found" - extract interesting information from what's provided.
Return ONLY valid JSON, no other text."""

        llm_response = llm.invoke(final_prompt)
        output_text = llm_response.content
        
        st.write("🤖 LLM Response received")

        try:
            # Remove markdown code blocks if present
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', output_text, re.DOTALL)
            if json_match:
                output_text = json_match.group(1)
            
            # Replace smart quotes with regular quotes
            output_text = output_text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
            
            parsed = parser.parse(output_text)

            # --- Display on screen ---
            st.markdown("### ✅ Research Result")
            st.markdown(f"**Topic:** {parsed.topic}")

            st.markdown("**🧠 Research Exploration:**")
            st.markdown(parsed.exploration)

            st.markdown("**📌 Summary (Points):**")
            for point in parsed.summary:
                st.markdown(f"- {point}")

            st.markdown("**🔗 Sources:**")
            for src in parsed.sources:
                st.markdown(f"- [{src}]({src})")

            st.markdown(f"**🛠 Tools Used:** {', '.join(parsed.tools_used)}")

            # Save to text file if selected
            if "Save to File" in selected_tools:
                save_tool.func(parsed.exploration)
                st.success("Research exploration saved to file!")

            # --- Markdown for PDF ---
            md_content = f"""
**Topic:** {parsed.topic}

**Research Exploration:**

{parsed.exploration}

**Summary:**

{chr(10).join([f"- {pt}" for pt in parsed.summary])}

**Sources:**
{chr(10).join([f"- {src}" for src in parsed.sources])}

**Tools Used:** {', '.join(parsed.tools_used)}
"""

            # Download as text file (Streamlit Cloud compatible)
            st.download_button(
                "📄 Download as Text File",
                md_content,
                file_name=f"research_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"❌ Failed to parse structured response: {e}")
            st.markdown("**Debug Info:**")
            st.markdown("**Raw LLM Response:**")
            st.code(output_text if output_text else "[EMPTY]", language="text")
            st.info("💡 The LLM may not be returning proper JSON. Try rephrasing your query.")
