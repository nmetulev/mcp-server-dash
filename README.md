# Dropbox Dash MCP Server

An MCP server that exposes Dropbox Dash search and file metadata via STDIO using the Python MCP server library (`fastmcp`). Authenticate with Dropbox, then search across all company content and fetch detailed file metadata and content.

## Tools Implemented

- `dash_get_auth_url`
  - Summary: Start Dropbox OAuth; returns the authorization URL.
  - Args: none
  - Returns (text): A short instruction message followed by the URL.
  - Notes: Use when not yet authenticated or when a token has expired. After approval in the browser, call `dash_authenticate` with the one-time code. Tokens are cached locally, so this is typically a one-time setup.

- `dash_authenticate`
  - Summary: Complete OAuth using the one-time authorization code.
  - Args:
    - `auth_code` (string, required)
  - Returns (text): Account display name and email on success; a human-readable error on failure.
  - Notes: Persists a token for subsequent tool calls. Typically only needed once until the token expires or is revoked.

- `dash_company_search`
  - Summary: Search company content indexed by Dropbox Dash.
  - Args:
    - `query` (string, required) — search text
    - `file_type` (string or null, optional) — one of: `document`, `image`, `video`, `audio`, `pdf`, `presentation`, `spreadsheet`; or `null` for no filter. Default: `null`. The value `document` is also treated as no filter.
    - `max_results` (integer, optional) — default `20`, range `1..100`
  - Returns (text): A formatted list of results. Each result includes labeled fields such as `UUID:`, `Type:`, `URL:`, `Preview:`, `Description:`, `File Type:`, `MIME Type:`, `Source:`, `Creator:`, `Last Modified By:`, `Updated:`, `Source Updated:`, `Relevance:`, `Source ID:`. Results are separated by a divider line.
  - Errors: Human-readable messages for invalid parameters or missing authentication.

- `dash_get_file_details`
  - Summary: Fetch detailed metadata (and optional content snippet) for a result UUID.
  - Args:
    - `uuid` (string, required) — UUID from search results
  - Returns (text): A summary with labeled fields (Title, Link, Updated, Source Updated, MIME Type, Source, Creator, Last Modified By). Media sections are included when present (Video/Image metadata). Content, when available, is shown with a MIME type and may be truncated to ~20,000 characters.
  - Errors: Human-readable messages for missing authentication or unknown UUID.

### First-Time (or Re-Auth) Flow

If the user is not yet authenticated (or the token has expired):
1) `dash_get_auth_url` → open the URL and approve access.
2) `dash_authenticate(auth_code)` → store the token.
3) Proceed with `dash_company_search(...)` and `dash_get_file_details(uuid)`.

## Prerequisites

Before installing and running the MCP server, you need to create a Dropbox app to obtain API credentials:

1. Go to [dropbox.com/developers/apps](https://www.dropbox.com/developers/apps)
2. Click on **Create app**
3. Select **Scoped access** as the API type
4. Choose **Full Dropbox** access
5. Give your app a name
6. After creating the app, go to the **Permissions** tab and enable:
   - `files.metadata.read`
   - `files.content.read`
7. Take note of the **App key** and **App secret** values from the **Settings** tab (you'll need these for configuration)

These credentials will be used as `APP_KEY` and `APP_SECRET` in the installation steps below.

## Requirements

- Python 3.10 or higher
- Dropbox Dash API credentials (Client ID and Client Secret)
- Network access to Dropbox APIs

## Installation

### Clone the repository:

```
git clone https://github.com/dropbox/mcp-server-dash
cd mcp-server-dash
```

### Install `uv` for virtual environment and dependency management:

**macOS (Homebrew)**
```
brew install uv
```

**macOS/Linux**:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```
irm https://astral.sh/uv/install.ps1 | iex
```

### Set up the virtual environment and install dependencies
```
uv sync
```

### Provide credentials (environment or `.env`)
```bash
export APP_KEY=your_dropbox_client_id
export APP_SECRET=your_dropbox_client_secret
# or create a .env file with APP_KEY and APP_SECRET
# e.g., copy the example file:
cp .env.example .env
```

## Usage

### Running the MCP Server in STDIO mode
```bash
uv run src/mcp_server_dash.py
```

Authenticate via tools: call dash_get_auth_url, then dash_authenticate with the code. A token is stored at `dropbox_token.json` in the project directory (legacy path `data/dropbox_token.json` is also supported for loading).

### Common MCP Server Configuration

For most MCP clients, including Claude and Cursor, you need to insert the below JSON 
configuration into a specific configuration file. See the specific instructions for 
Claude and Cursor below.

❗ **Important:** Update the configuration below with the path to your installation and with your `APP_KEY` and `APP_SECRET`.

MCP Server Configuration:
```json
{
  "mcpServers": {
    "Dropbox Dash Search": {
      "command": "uv",
      "args": [
          "--directory",
          "/path/to/mcp-server-dash/",
          "run", 
          "src/mcp_server_dash.py"
      ],
      "env": {
        "APP_KEY": "your_dropbox_client_id",
        "APP_SECRET": "your_dropbox_client_secret"
      }
    }
  }
}
```

### Using Claude as the Client
- Open `Claude Desktop → Settings → Developer → Local MCP Servers → Edit Config`
- Add the JSON MCP Server configuration shown above.
- Restart Claude Desktop after saving the config.

### Using Cursor as the Client

- Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows) to open the Command Palette
- Type "View: Open MCP Settings"
- Add the JSON MCP Server Configuration to the `mcp.json` file as instructed.

### Using Goose as the Client

- Select `Extensions → Add custom extension`
- Fill out the form:
  - **Extension Name**: Dropbox Dash Search
  - **Type**: STDIO
  - **Description**: Provide company context to your workflows
  - **Command**: `uv --directory /path/to/mcp-server-dash/ run src/mcp_server_dash.py`
  - **Environment**:
    - `APP_KEY`: Your Dropbox Client ID
    - `APP_SECRET`: Your Dropbox Client Secret
- Click `Add Extension`


## Development 

Install dev tools (ruff, black, mypy, pytest, coverage) using uv:

```bash
uv pip install -e ".[dev]"
```

### Lint, Format, Type-check

Run checks (via uv):

```bash
# Lint (imports, style, bugbear, etc.)
uv run ruff check .

# Format (apply changes)
uv run black .

# Type-check
uv run mypy src
```

Tip: use `uv run ruff format .` (or `uv run black .`) to auto-format, and `uv run ruff check --fix .` to apply safe autofixes.

### Testing & Coverage

Run the test suite (quiet mode with coverage summary) using uv:

```bash
uv run pytest
# or explicitly with coverage flags
uv run pytest -q --cov=src --cov-report=term-missing
```

### Debugging
You can inspect and debug the server with the Model Context Protocol Inspector:

```bash
npx @modelcontextprotocol/inspector uv run src/mcp_server_dash.py
```

Ensure `APP_KEY` and `APP_SECRET` are set in your environment or `.env` before running the inspector.

## License

Apache License 2.0

Copyright (c) 2025 Dropbox, Inc.

See [LICENSE](LICENSE) for details.
