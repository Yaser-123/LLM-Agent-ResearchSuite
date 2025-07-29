from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchResults
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
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

# ========== Tool: Web Search (DuckDuckGo with links) ==========
duckduckgo = DuckDuckGoSearchResults()

def search_with_links(query: str) -> str:
    results = duckduckgo.run(query)
    if not results:
        return "No search results found."

    output = ""
    for r in results[:3]:  # Get top 3 results only
        title = r.get("title", "No Title")
        link = r.get("link", "")
        snippet = r.get("snippet", "")
        output += f"{title}\n{snippet}\nSource: {link}\n\n"

    return output.strip()

search_tool = Tool(
    name="search",
    func=search_with_links,
    description="Search the web for up-to-date info and sources using DuckDuckGo. Input should be a search query."
)

# ========== Tool: Wikipedia Search with Source Link ==========
def wiki_with_link(topic: str) -> str:
    api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=300)
    summary = api_wrapper.run(topic)
    wiki_url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
    return f"{summary}\nSource: {wiki_url}"

wiki_tool = Tool(
    name="wikipedia_lookup",
    func=wiki_with_link,
    description="Search Wikipedia for concise information and article link. Input should be a topic or keyword."
)
