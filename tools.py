from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import Tool
from datetime import datetime

# ========== Tool: Save to File ==========
def save_to_txt(data: str, filename: str = "research_output.txt") -> str:
    """
    Saves the given data to a text file with a timestamp.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)

    return f"✅ Data successfully saved to {filename}"

save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Use this to save structured research data to a text file. Input should be a full summary or result string."
)

# ========== Tool: Web Search (DuckDuckGo with fallback) ==========
try:
    from langchain_community.tools import DuckDuckGoSearchRun
    search = DuckDuckGoSearchRun()
    search_func = search.run
except Exception:
    # Fallback for Streamlit Cloud where DuckDuckGo might not work
    def search_func(query: str) -> str:
        return f"Search for '{query}' - DuckDuckGo unavailable. Please use Wikipedia tool for research."

search_tool = Tool(
    name="search",
    func=search_func,
    description="Search the web for up-to-date information using DuckDuckGo. Input should be a search query."
)

# ========== Tool: Wikipedia Search ==========
api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=5000)

wiki_tool = Tool(
    name="wikipedia_lookup",
    func=WikipediaQueryRun(api_wrapper=api_wrapper).run,
    description="Search Wikipedia for concise and relevant information. Input should be a topic or keyword."
)
