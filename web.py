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
from langchain.agents import create_tool_calling_agent, AgentExecutor
from datetime import datetime
from io import BytesIO
from xhtml2pdf import pisa
import markdown2

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
            llm = ChatGoogleGenerativeAI(
                model="models/gemini-2.5-flash",
                google_api_key=st.secrets["GOOGLE_API_KEY"],
                stream=False
            )
        elif llm_choice == "Claude 3.5":
            llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
        else:
            llm = ChatOpenAI(model="gpt-4")

        parser = PydanticOutputParser(pydantic_object=ResearchResponse)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are an AI research assistant.
Use the tools provided to deeply explore the user's query.
Return the output strictly as structured JSON like this. If tool responses contain URLs or links, include them in the 'sources' list:

```json
{{
  "topic": "<Main Topic Title>",
  "exploration": "<Detailed research findings in paragraph>",
  "summary": [
    "<point 1>",
    "<point 2>",
    "..."
  ],
  "sources": [
    "<full clickable URL>",
    "<full clickable URL>"
  ],
  "tools_used": ["tool1", "tool2"]
}}
```

{agent_scratchpad}
"""),
            ("human", "{query}"),
        ]).partial(query=query)

        selected_tool_instances = [tools[t] for t in selected_tools if t != "Save to File"]

        agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=selected_tool_instances)
        agent_executor = AgentExecutor(agent=agent, tools=selected_tool_instances, verbose=True)

        result = agent_executor.invoke({"query": query})

        try:
            parsed = parser.parse(result["output"])

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

            # Convert to PDF
            html = markdown2.markdown(md_content)
            pdf = BytesIO()
            pisa.CreatePDF(html, dest=pdf)
            pdf.seek(0)

            st.download_button("📄 Download as PDF", pdf, file_name=f"research_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")

        except Exception as e:
            st.error(f"❌ Failed to parse structured response: {e}")
