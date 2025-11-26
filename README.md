# PR Review Agent 🤖

An automated GitHub Pull Request Review Agent that uses a multi-agent architecture to analyze code changes and generate structured, actionable review comments.

## Features

- **Multi-Agent Architecture**: Specialized agents for different aspects of code review:
  - 🔒 **Security Agent**: Identifies vulnerabilities, injection risks, credential exposure
  - ⚡ **Performance Agent**: Finds bottlenecks, inefficient algorithms, resource issues
  - 🎨 **Code Quality Agent**: Reviews style, readability, best practices
  - 🧠 **Logic Agent**: Detects bugs, edge cases, incorrect implementations
  - 📚 **Documentation Agent**: Checks for missing or outdated documentation

- **GitHub Integration**: Full GitHub API support to:
  - Fetch PR diffs automatically
  - Post review comments back to PRs
  - Track PR metadata

- **Diff Parser**: Robust unified diff parser that:
  - Extracts changed lines with context
  - Identifies programming language
  - Groups changes by file and hunk

- **REST API**: FastAPI-based backend with:
  - OpenAPI documentation
  - Health checks
  - Review history

- **Web UI**: Simple interface for testing reviews

## Architecture

```
pr-review-agent/
├── app/
│   ├── agents/                 # Multi-agent implementation
│   │   ├── base_agent.py       # Base agent class
│   │   ├── security_agent.py   # Security vulnerability detection
│   │   ├── performance_agent.py # Performance issue detection
│   │   ├── code_quality_agent.py # Code quality analysis
│   │   ├── logic_agent.py      # Logic/bug detection
│   │   └── documentation_agent.py # Documentation review
│   ├── models/                 # Data models
│   │   ├── database.py         # SQLAlchemy models
│   │   └── schemas.py          # Pydantic schemas
│   ├── orchestrator/           # Multi-agent orchestration
│   │   └── review_orchestrator.py
│   ├── services/               # External services
│   │   ├── diff_parser.py      # Git diff parser
│   │   ├── github_client.py    # GitHub API client
│   │   └── llm_provider.py     # Gemini LLM wrapper
│   ├── config.py               # Configuration
│   └── main.py                 # FastAPI application
├── static/                     # Web UI
│   └── index.html
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.10+
- Google Gemini API key
- GitHub Personal Access Token (for GitHub PR reviews)

## Installation

1. **Clone the repository**:
   ```bash
   cd pr-review-agent
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```
   GOOGLE_API_KEY=your_gemini_api_key
   GITHUB_TOKEN=your_github_token  # Optional, for GitHub PR reviews
   ```

## Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage

### 1. Review a GitHub PR (via API)

```bash
curl -X POST "http://localhost:8000/api/review/github" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_owner": "owner",
    "repo_name": "repo",
    "pr_number": 123
  }'
```

### 2. Review a Manual Diff

```bash
curl -X POST "http://localhost:8000/api/review/diff" \
  -H "Content-Type: application/json" \
  -d '{
    "diff_content": "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,4 @@\n def hello():\n-    print(\"Hello\")\n+    print(\"Hello World\")\n+    return True"
  }'
```

### 3. Using the Web UI

1. Open http://localhost:8000 in your browser
2. Choose "Review GitHub PR" or "Review Diff"
3. Enter the details and click "Review"
4. View the structured review results

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/review/github` | Review a GitHub PR |
| POST | `/api/review/diff` | Review a manual diff |
| GET | `/api/review/{id}` | Get review by ID |
| GET | `/api/reviews` | List all reviews |
| DELETE | `/api/review/{id}` | Delete a review |
| GET | `/api/test/llm` | Test LLM connection |
| GET | `/api/test/github` | Test GitHub connection |

## Response Format

```json
{
  "success": true,
  "review_id": 1,
  "files_reviewed": 3,
  "summary": {
    "total_issues": 5,
    "severity_counts": {
      "critical": 0,
      "high": 1,
      "medium": 2,
      "low": 1,
      "info": 1
    },
    "category_counts": {
      "security": 1,
      "performance": 1,
      "logic": 1,
      "code_quality": 2,
      "documentation": 0
    },
    "overall_rating": "changes_requested"
  },
  "findings": [
    {
      "file_path": "src/utils.py",
      "line_number": 42,
      "category": "security",
      "severity": "high",
      "title": "SQL Injection Vulnerability",
      "description": "User input is directly concatenated into SQL query...",
      "original_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
      "suggested_code": "query = \"SELECT * FROM users WHERE id = %s\"\ncursor.execute(query, (user_id,))",
      "agent_name": "Security Agent"
    }
  ]
}
```

## Configuration Options

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Optional |
| `DATABASE_URL` | SQLite database URL | `sqlite:///./pr_reviews.db` |
| `DEBUG` | Enable debug mode | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

## How It Works

1. **Diff Parsing**: The system parses the unified diff format to extract:
   - Changed files
   - Added/removed lines
   - Line numbers and context
   - Programming language detection

2. **Multi-Agent Analysis**: Each specialized agent analyzes the code:
   - Receives code context and diff
   - Applies domain-specific rules and heuristics
   - Uses LLM (Gemini) for intelligent analysis
   - Returns structured findings

3. **Orchestration**: The orchestrator:
   - Coordinates all agents (parallel execution)
   - Aggregates findings
   - Removes duplicates
   - Generates summary statistics

4. **Storage & Response**: Results are:
   - Stored in SQLite for history
   - Returned as structured JSON
   - Optionally posted to GitHub

## Extending the System

### Adding a New Agent

1. Create a new agent file in `app/agents/`:
```python
from app.agents.base_agent import BaseReviewAgent, AgentFinding

class CustomAgent(BaseReviewAgent):
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            name="Custom Agent",
            role="Custom Analysis",
            goal="Your agent's goal"
        )
    
    def get_system_prompt(self) -> str:
        return """Your system prompt here..."""
    
    def analyze(self, code_context):
        # Your analysis logic
        pass
```

2. Register in `app/agents/__init__.py`
3. Add to orchestrator in `app/orchestrator/review_orchestrator.py`

## License

MIT License
