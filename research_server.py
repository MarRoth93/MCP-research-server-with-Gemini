
import arxiv
import json
import os
from typing import List
from mcp.server.fastmcp import FastMCP
import re
from pathlib import Path
from docling.document_converter import DocumentConverter
from mcp.types import Resource

# --- Constants for directories ---
PAPER_DIR = "papers"
PAPER_TXT_DIR = Path("G:/Meine Ablage/02_Marco/Paper to read/parsed")
PARSED_DIR = PAPER_TXT_DIR

# Initialize FastMCP server
mcp = FastMCP("research", dynamic_resource_resolver=True)


@mcp.tool()
def search_papers(topic: str, max_results: int = 1, search_pool_size: int = 50) -> str:
    client = arxiv.Client()
    print(f"Fetching {search_pool_size} most relevant papers for '{topic}'...")
    search = arxiv.Search(
        query=topic,
        max_results=search_pool_size,
        sort_by=arxiv.SortCriterion.Relevance
    )
    relevant_papers = list(client.results(search))
    if not relevant_papers:
        return f"No papers found for the topic '{topic}'."

    print("Sorting relevant papers by most recent date...")
    relevant_papers.sort(key=lambda paper: paper.published, reverse=True)
    final_papers = relevant_papers[:max_results]

    safe_topic = re.sub(r'[^\w\-_. ]', '_', topic.lower().strip().replace(" ", "_"))

    # Save to internal paper dir
    paper_dir_path = os.path.join(PAPER_DIR, safe_topic)
    os.makedirs(paper_dir_path, exist_ok=True)
    file_path = os.path.join(paper_dir_path, "papers_info.json")

    # Also save to parsed dir
    parsed_topic_path = os.path.join(PAPER_TXT_DIR, safe_topic)
    os.makedirs(parsed_topic_path, exist_ok=True)
    parsed_file_path = os.path.join(parsed_topic_path, "papers_info.json")

    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    try:
        with open(parsed_file_path, "r") as parsed_file:
            parsed_info = json.load(parsed_file)
    except (FileNotFoundError, json.JSONDecodeError):
        parsed_info = {}

    output_results = []
    for paper in final_papers:
        short_id = paper.get_short_id()
        if short_id not in papers_info:
            paper_info = {
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'summary': paper.summary.replace("\n", " "),
                'pdf_url': paper.pdf_url,
                'published': str(paper.published.date())
            }
            papers_info[short_id] = paper_info
            parsed_info[short_id] = paper_info

        output_entry = (
            f"Title: {paper.title}, Paper ID: {short_id}\n"
            f"Published: {paper.published.date()}"
        )
        output_results.append(output_entry)

    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=4)

    with open(parsed_file_path, "w") as parsed_file:
        json.dump(parsed_info, parsed_file, indent=4)

    return "\n\n".join(output_results)

@mcp.tool()
def extract_info(paper_id: str) -> str:
    search_dirs = [Path(PAPER_DIR), Path(PAPER_TXT_DIR)]

    for base_dir in search_dirs:
        for dir_ in base_dir.iterdir():
            file_path = dir_ / "papers_info.json"
            if file_path.is_file():
                try:
                    with open(file_path) as f:
                        info = json.load(f)
                    if paper_id in info:
                        return json.dumps(info[paper_id], indent=2)
                except json.JSONDecodeError:
                    continue

    return f"No information stored for paper ID {paper_id!r}."


@mcp.tool()
def file_parsing(paper_id: str) -> str:
    INSTRUCTION_TEXT = """
You are a research assistant with expertise in summarizing and critically evaluating academic papers. Carefully read the research paper provided and structure your analysis in the following clear, concise, and thorough manner:

Overall Summary:
Provide a brief, high-level summary capturing the main purpose and significance of the paper.

Goal of the Paper:
Clearly state the primary research question or objective that the authors aimed to address.

Methods:
Summarize the methodology clearly, detailing the experimental design, data collection techniques, analytical approaches, and computational methods used by the authors.

Results:
Highlight the key findings and outcomes presented in the paper, focusing on the data-supported conclusions and significant experimental results.

Novelty of the Research:
Discuss explicitly what makes this research innovative or unique compared to existing studies. Clarify any groundbreaking methods, insights, or conclusions introduced.

Future Research Implications:
Suggest potential avenues for future research that stem from the findings of this paper. Describe clearly how the current results can guide or inform subsequent studies.

Relevance to Current Research:
Contextualize how this research fits into the broader landscape of the field. Explain its alignment or deviation from current trends, theories, and practices.

Limitations:
Clearly outline any limitations identified in the paper, such as methodological constraints, potential biases, assumptions, or gaps in the research approach that could impact the validity or generalizability of the findings.

Provide each section distinctly and ensure your analysis is clear, insightful, and comprehensive.

I will now paste the text of the research paper below.
"""

    pdf_url = None
    paper_title = None

    for dir_ in Path(PAPER_DIR).iterdir():
        if not dir_.is_dir():
            continue
        file_path = dir_ / "papers_info.json"
        if file_path.is_file():
            try:
                with open(file_path) as f:
                    info = json.load(f)
                if paper_id in info:
                    paper_info_dict = info[paper_id]
                    pdf_url = paper_info_dict.get('pdf_url')
                    paper_title = paper_info_dict.get('title')
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                continue

    if not pdf_url or not paper_title:
        return f"Could not find complete information (URL and Title) for paper ID {paper_id}. Please run `search_papers` first."

    try:
        print(f"Attempting to parse PDF from: {pdf_url}")
        converter = DocumentConverter()
        result = converter.convert(pdf_url)
        markdown_content = result.document.export_to_markdown()
    except Exception as e:
        return f"Failed to parse the document for paper ID {paper_id}. Error: {e}"

    # Step 3: Sanitize title
    safe_title = re.sub(r'[^\w\-_]', '_', paper_title.strip())
    safe_title = re.sub(r'_+', '_', safe_title).strip('_')
    safe_title = safe_title[:150]

    os.makedirs(PARSED_DIR, exist_ok=True)
    output_filename = f"{safe_title}.txt"
    output_filepath = os.path.join(PARSED_DIR, output_filename)

    with open(output_filepath, 'w', encoding='utf-8') as file:
        file.write(f"# {paper_title}\n\n" + INSTRUCTION_TEXT.strip() + "\n\n" + markdown_content)

    return f"Successfully parsed paper {paper_id} and saved markdown to '{output_filepath}'."



@mcp.prompt()
def extract_website(url: str, filename: str) -> str:
    """Fetch a web page and save a cleaned-up Markdown version to the
    'websites' folder inside my MCP filesystem root."""
    return f"""fetch information from the website {url} and save itr as a md file in my directory 'G:\\Meine Ablage\\02_Marco\\Paper to read\\websites'. Name the file {filename}"""


    
@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """Generate a prompt for Gemini to find and discuss academic papers on a specific topic."""
    return f"""Search for {num_papers} academic papers about '{topic}' using the search_papers tool. Follow these instructions:
    1. First, search for papers using search_papers(topic='{topic}', max_results={num_papers})
    2. For each paper found, extract and organize the following information:
       - Paper title
       - Authors
       - Publication date
       - Brief summary of the key findings
       - Main contributions or innovations
       - Methodologies used
       - Relevance to the topic '{topic}'
    
    3. Provide a comprehensive summary that includes:
       - Overview of the current state of research in '{topic}'
       - Common themes and trends across the papers
       - Key research gaps or areas for future investigation
       - Most impactful or influential papers in this area
    
    4. Organize your findings in a clear, structured format with headings and bullet points for easy readability.
    
    Please present both detailed information about each paper and a high-level synthesis of the research landscape in {topic}."""


@mcp.resource("papers://paper")
def list_parsed_papers() -> str:
    """
    Lists all .txt files from the parsed papers folder in markdown bullet list format.
    """
    if not PAPER_TXT_DIR.exists():
        return "⚠️ Parsed directory not found."

    txt_files = [f.name for f in PAPER_TXT_DIR.glob("*.txt")]

    if not txt_files:
        return "# Parsed Papers 📄\n\n_No parsed papers found._"

    content = "# Parsed Papers 📄\n"
    for filename in sorted(txt_files):
        content += f"- {filename}\n"

    return content.strip()


@mcp.resource("papers://folder")
def get_available_folders() -> str:
    """
    List all available topic folders in the parsed papers directory.
    Each folder should contain a `papers_info.json` file.
    """
    folders = []

    if PAPER_TXT_DIR.exists():
        for topic_path in PAPER_TXT_DIR.iterdir():
            if topic_path.is_dir() and (topic_path / "papers_info.json").exists():
                folders.append(topic_path.name)

    content = "# Available Topics (Parsed Directory)\n\n"
    if folders:
        for folder in sorted(folders):
            content += f"- {folder}\n"
        content += "\nUse `@<folder>` to access papers in that topic.\n"
    else:
        content += "_No topic folders with papers found._"

    return content.strip()


@mcp.resource("papers://{topic}")
def get_topic_from_parsed(topic: str) -> str:
    safe_topic = topic.lower().replace(" ", "_")
    folder_path = PAPER_TXT_DIR / safe_topic
    papers_file = folder_path / "papers_info.json"

    if not papers_file.exists():
        return f"# No papers found for topic '{safe_topic}'.\n\nTry running `search_papers(topic='{safe_topic}')` first."

    try:
        with open(papers_file, 'r', encoding='utf-8') as f:
            papers_data = json.load(f)
    except json.JSONDecodeError:
        return f"# Error reading papers data for topic '{safe_topic}' — the file is corrupted."

    content = f"# Papers in {safe_topic}\n\n"
    content += f"Total papers: {len(papers_data)}\n\n"

    for paper_id, paper_info in papers_data.items():
        content += f"## {paper_info['title']}\n"
        content += f"- **Paper ID**: {paper_id}\n"
        content += f"- **Authors**: {', '.join(paper_info['authors'])}\n"
        content += f"- **Published**: {paper_info['published']}\n"
        content += f"- **PDF URL**: [{paper_info['pdf_url']}]({paper_info['pdf_url']})\n\n"
        content += f"### Summary\n{paper_info['summary'][:500]}...\n\n"
        content += "---\n\n"

    return content.strip()


# -- Start the MCP server --
if __name__ == "__main__":
    mcp.run(transport='stdio')



