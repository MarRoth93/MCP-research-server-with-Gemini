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

---



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

2. **`research_server.py`**

   ```python
   PAPER_TXT_DIR = Path("add path here")  # Set this to your parsed papers directory
   ```

3. **Inside Prompts**
   Look for any text that includes `'add path here'` and update it with your preferred local directory path.

 Tip: Use absolute paths like `C:/Users/yourname/Documents/parsed` for best results.

