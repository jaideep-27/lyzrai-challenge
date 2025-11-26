"""
Base Agent Class - Foundation for all review agents
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import re
import time


@dataclass
class AgentFinding:
    """A finding from an agent's analysis"""
    file_path: str
    line_number: Optional[int]
    line_range_start: Optional[int]
    line_range_end: Optional[int]
    category: str
    severity: str
    title: str
    description: str
    original_code: Optional[str] = None
    suggested_code: Optional[str] = None
    agent_name: Optional[str] = None


class BaseReviewAgent(ABC):
    """Base class for all code review agents"""
    
    def __init__(self, llm, name: str, role: str, goal: str):
        self.llm = llm
        self.name = name
        self.role = role
        self.goal = goal
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def analyze(self, code_context: Dict[str, Any]) -> List[AgentFinding]:
        """Analyze code and return findings"""
        pass
    
    def _create_analysis_prompt(self, code_context: Dict[str, Any]) -> str:
        """Create the analysis prompt with code context"""
        file_path = code_context.get("file_path", "unknown")
        language = code_context.get("language", "unknown")
        diff_content = code_context.get("diff_content", "")
        additions = code_context.get("additions", [])
        
        # Format additions for the prompt
        additions_text = "\n".join([
            f"Line {a.get('line_number', '?')}: {a.get('content', '')}"
            for a in additions
        ]) if additions else "No additions"
        
        return f"""
Analyze the following code changes:

**File:** {file_path}
**Language:** {language}

**Diff Content:**
```
{diff_content}
```

**Added Lines:**
{additions_text}

Provide your analysis in the following JSON format (respond ONLY with valid JSON, no markdown):
{{
    "findings": [
        {{
            "line_number": <int or null>,
            "line_range_start": <int or null>,
            "line_range_end": <int or null>,
            "severity": "<critical|high|medium|low|info>",
            "title": "<short title>",
            "description": "<detailed description of the issue>",
            "original_code": "<problematic code snippet or null>",
            "suggested_code": "<suggested fix or null>"
        }}
    ]
}}

If no issues are found, return: {{"findings": []}}
"""
    
    def _parse_llm_response(self, response: str, file_path: str, category: str) -> List[AgentFinding]:
        """Parse LLM response into AgentFindings"""
        findings = []
        
        try:
            # Try to extract JSON from the response
            # Handle markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_str = response.strip()
            
            # Clean up the JSON string
            json_str = json_str.strip()
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            data = json.loads(json_str)
            
            for finding in data.get("findings", []):
                findings.append(AgentFinding(
                    file_path=file_path,
                    line_number=finding.get("line_number"),
                    line_range_start=finding.get("line_range_start"),
                    line_range_end=finding.get("line_range_end"),
                    category=category,
                    severity=finding.get("severity", "medium"),
                    title=finding.get("title", "Issue Found"),
                    description=finding.get("description", ""),
                    original_code=finding.get("original_code"),
                    suggested_code=finding.get("suggested_code"),
                    agent_name=self.name
                ))
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract information manually
            print(f"Warning: Failed to parse JSON from {self.name}: {e}")
            # Create a generic finding based on the response
            if response and len(response) > 50:
                findings.append(AgentFinding(
                    file_path=file_path,
                    line_number=None,
                    line_range_start=None,
                    line_range_end=None,
                    category=category,
                    severity="info",
                    title=f"{self.name} Analysis",
                    description=response[:500],
                    agent_name=self.name
                ))
        except Exception as e:
            print(f"Error parsing response from {self.name}: {e}")
        
        return findings
    
    def run(self, code_context: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent analysis"""
        start_time = time.time()
        
        try:
            findings = self.analyze(code_context)
            execution_time = time.time() - start_time
            
            return {
                "agent_name": self.name,
                "findings": [
                    {
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "line_range_start": f.line_range_start,
                        "line_range_end": f.line_range_end,
                        "category": f.category,
                        "severity": f.severity,
                        "title": f.title,
                        "description": f.description,
                        "original_code": f.original_code,
                        "suggested_code": f.suggested_code,
                        "agent_name": f.agent_name
                    }
                    for f in findings
                ],
                "execution_time_seconds": execution_time,
                "error": None
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "agent_name": self.name,
                "findings": [],
                "execution_time_seconds": execution_time,
                "error": str(e)
            }
