# MCP-research-server-with-Gemini


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

> 📝 Tip: Use absolute paths like `C:/Users/yourname/Documents/parsed` for best results.

---

Let me know if you want a `.env`-based version instead.
