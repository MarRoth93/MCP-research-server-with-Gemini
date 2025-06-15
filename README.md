# MCP-research-server-with-Gemini



## How to Run the Gemini MCP Chatbot

This project uses [`uv`] — a fast Python package manager and virtual environment tool — to manage dependencies and run your bot. Here’s how to set everything up from scratch.


### Prerequisites

* Python 3.11+ (>= 3.11 recommended)

---

### Step-by-Step Setup

1. **Clone this repository**

   ```bash
   git clone https://github.com/MarRoth93/MCP-research-server-with-Gemini
   cd your-repo-name
   ```

2. **Create a virtual environment using `uv`**

   ```bash
   uv venv
   ```

3. **Activate the virtual environment**

   * On **Windows**:

     ```bash
     .venv\Scripts\activate
     ```

   * On **macOS/Linux**:

     ```bash
     source .venv/bin/activate
     ```

4. **Install all required dependencies**

   ```bash
   uv pip install -e .
   ```

5. **Set your environment variables**

   Copy the provided `.env.example` file to `.env` and update it with your API key:

   ```bash
   cp .env.example .env
   # then edit .env and replace the placeholder with your key
   ```

---

### Start the Chatbot

Once everything is set up, you can launch the chatbot with:

```bash
uv run mcp_chatbot_gemini.py
```

You’ll see output indicating that servers and tools are loading. Once complete, you can interact with the Gemini bot in the terminal.
This chatbot calls Gemini using the `gemini-2.0-flash-exp` model by default.
You can change the `model` parameter in `mcp_chatbot_gemini.py` to use any other Gemini model.

---
## Tools

The chatbot communicates with several MCP servers to provide various
functions and prompts.

### Servers

- **filesystem** – exposes your `parsed` and `websites` folders so the bot can
  read and write files.
- **fetch** – simple HTTP fetch server for downloading content.
- **research** – runs `research_server.py` and supplies the tools listed below.

### Functions in `research_server.py`

- `search_papers(topic, max_results=1, search_pool_size=50)` – search arXiv and
  store paper metadata.
- `extract_info(paper_id)` – return stored details about a paper.
- `file_parsing(paper_id)` – convert a PDF to Markdown. This parse function
  adds a prompt before the parsed output so Gemini knows how to summarise it.

### Prompts

- `extract_website(url, filename)` – fetch a web page and save a Markdown
  snapshot.
- `generate_search_prompt(topic, num_papers=5)` – guide Gemini to research a
  topic using the above tools.

### Resources

- `papers://paper` – list parsed papers.
- `papers://folder` – list available topics.
- `papers://{topic}` – fetch papers for a specific topic.

## Path updates
### 🔧 Configuration Required: Add Your Local Paths

Some parts of this project require local filesystem paths to save and access papers and website content. For privacy and portability, these paths have been removed from the public repo.

To use the system, **you must update the following placeholders with your own local paths**:

1. **`server_config.json`**

   ```json
   "args": [
     "-y",
     "@modelcontextprotocol/server-filesystem",
     "add path here",   // Path to your 'parsed' folder
     "add path here"    // Path to your 'websites' folder
   ]
   ```
Example paths:

   ```json
   "args": [
     "-y",
     "@modelcontextprotocol/server-filesystem",
     "C:/ResearchData/parsed",
     "C:/ResearchData/websites"
   ]
   ```
   This assumes you have a `ResearchData` directory with `parsed` and `websites` subfolders.


2. **`research_server.py`**

   ```python
   PAPER_TXT_DIR = Path("add path here")  # Set this to your parsed papers directory
   ```
   Example:

   ```python
   PAPER_TXT_DIR = Path("C:/ResearchData/parsed")
   ```
   Make sure this matches the `parsed` folder path in your `server_config.json`.


3. **Inside Prompts**
   Look for any text that includes `'add path here'` and update it with your preferred local directory path.

 Tip: Use absolute paths like `C:/Users/yourname/Documents/parsed` for best results.

