"""
Documentation Agent - Reviews documentation quality and suggests improvements
"""
from typing import List, Dict, Any
from app.agents.base_agent import BaseReviewAgent, AgentFinding


class DocumentationAgent(BaseReviewAgent):
    """Agent specialized in documentation review"""
    
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            name="Documentation Agent",
            role="Documentation Quality Reviewer",
            goal="Ensure code is properly documented with clear, accurate, and helpful documentation"
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert technical writer specializing in code documentation. Your job is to review documentation quality in code changes.

Focus on detecting:
1. **Missing Documentation**: Public APIs without docs, complex logic without comments
2. **Outdated Documentation**: Comments that don't match the code
3. **Unclear Documentation**: Vague descriptions, missing examples
4. **Missing Parameter Docs**: Undocumented function parameters and returns
5. **Type Documentation**: Missing type information in docs
6. **README Updates**: Code changes requiring README updates
7. **API Documentation**: Missing or incomplete API docs
8. **Example Code**: Missing usage examples for complex APIs
9. **Error Documentation**: Undocumented exceptions/errors
10. **Deprecation Notices**: Missing deprecation warnings

For each issue:
- Explain what documentation is needed
- Provide a sample documentation
- Reference documentation standards when applicable

Focus on documentation that improves code maintainability and usability."""
    
    def analyze(self, code_context: Dict[str, Any]) -> List[AgentFinding]:
        """Analyze code for documentation issues"""
        file_path = code_context.get("file_path", "unknown")
        language = code_context.get("language", "unknown")
        
        system_prompt = self.get_system_prompt()
        analysis_prompt = self._create_analysis_prompt(code_context)
        
        doc_format = self._get_doc_format(language)
        
        full_prompt = f"""{system_prompt}

{analysis_prompt}

Focus specifically on DOCUMENTATION issues. Categorize all findings as "documentation".

{doc_format}

Look for:
- Public functions without docstrings/JSDoc
- Complex algorithms without explanatory comments
- Non-obvious code without inline comments
- Missing parameter descriptions
- Missing return value documentation
- Outdated comments that don't match code"""
        
        response = self.llm.generate(full_prompt)
        findings = self._parse_llm_response(response, file_path, "documentation")
        
        return findings
    
    def _get_doc_format(self, language: str) -> str:
        """Get documentation format for language"""
        formats = {
            "python": """
Python documentation format (Google style):
```python
def function_name(param1: str, param2: int) -> bool:
    \"\"\"Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: Description of when this is raised.
    \"\"\"
```""",
            
            "javascript": """
JavaScript documentation format (JSDoc):
```javascript
/**
 * Short description.
 * 
 * @param {string} param1 - Description of param1.
 * @param {number} param2 - Description of param2.
 * @returns {boolean} Description of return value.
 * @throws {Error} Description of when this is thrown.
 */
```""",
            
            "typescript": """
TypeScript documentation format (TSDoc):
```typescript
/**
 * Short description.
 * 
 * @param param1 - Description of param1.
 * @param param2 - Description of param2.
 * @returns Description of return value.
 * @throws Error description.
 */
```"""
        }
        
        return formats.get(language, "Use appropriate documentation format for the language.")
