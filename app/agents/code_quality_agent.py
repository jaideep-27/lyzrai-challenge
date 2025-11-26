"""
Code Quality Agent - Reviews code style, readability, and best practices
"""
from typing import List, Dict, Any
from app.agents.base_agent import BaseReviewAgent, AgentFinding


class CodeQualityAgent(BaseReviewAgent):
    """Agent specialized in code quality and best practices"""
    
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            name="Code Quality Agent",
            role="Code Quality & Standards Reviewer",
            goal="Ensure code follows best practices, is readable, maintainable, and well-structured"
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert code reviewer specializing in code quality and best practices. Your job is to identify code quality issues in code changes.

Focus on detecting:
1. **Readability Issues**: Unclear naming, complex expressions, missing comments
2. **Code Smells**: Long functions, deep nesting, god classes, magic numbers
3. **DRY Violations**: Duplicated code, repeated patterns
4. **SOLID Principles**: Single responsibility, open/closed, etc.
5. **Error Handling**: Missing try-catch, swallowed exceptions, unclear error messages
6. **Documentation**: Missing docstrings, outdated comments, unclear APIs
7. **Testing Concerns**: Untestable code, missing edge cases
8. **Naming Conventions**: Inconsistent naming, unclear variable names
9. **Code Organization**: Misplaced logic, poor module structure
10. **Type Safety**: Missing type hints, unsafe type operations

For each issue:
- Explain why it matters for maintainability
- Reference relevant design patterns or principles
- Provide a clear refactoring suggestion
- Rate impact on code quality

Be constructive - focus on actionable improvements."""
    
    def analyze(self, code_context: Dict[str, Any]) -> List[AgentFinding]:
        """Analyze code for quality issues"""
        file_path = code_context.get("file_path", "unknown")
        language = code_context.get("language", "unknown")
        
        system_prompt = self.get_system_prompt()
        analysis_prompt = self._create_analysis_prompt(code_context)
        
        # Add quality-specific instructions
        language_conventions = self._get_language_conventions(language)
        
        full_prompt = f"""{system_prompt}

{analysis_prompt}

Focus specifically on CODE QUALITY issues. Categorize all findings as "code_quality".

{language_conventions}

Common patterns to look for:
- Functions longer than 20-30 lines
- More than 3 levels of nesting
- Variables with single-letter or unclear names
- Missing error handling
- Commented-out code
- Hardcoded values (magic numbers/strings)
- Missing type annotations
- Overly complex boolean expressions"""
        
        response = self.llm.generate(full_prompt)
        findings = self._parse_llm_response(response, file_path, "code_quality")
        
        return findings
    
    def _get_language_conventions(self, language: str) -> str:
        """Get language-specific coding conventions"""
        conventions = {
            "python": """
Python conventions (PEP 8 & PEP 257):
- snake_case for functions and variables
- PascalCase for classes
- UPPER_CASE for constants
- Docstrings for all public functions/classes
- Type hints (PEP 484)
- 79 character line limit (99 for code)
- Use `is` for None comparisons
- Prefer `with` for resource management""",
            
            "javascript": """
JavaScript conventions:
- camelCase for variables and functions
- PascalCase for classes and components
- UPPER_CASE for constants
- Use const by default, let when needed
- Avoid var
- Prefer arrow functions for callbacks
- Use template literals
- Prefer async/await over raw promises""",
            
            "typescript": """
TypeScript conventions:
- Same as JavaScript conventions
- Explicit return types for functions
- Use interfaces for object shapes
- Avoid `any` type
- Use type unions over enums when appropriate
- Prefer readonly properties when possible""",
            
            "java": """
Java conventions:
- camelCase for methods and variables
- PascalCase for classes
- UPPER_CASE for constants
- Javadoc for public APIs
- Use Optional for nullable returns
- Prefer interfaces over abstract classes
- Follow effective Java guidelines""",
            
            "go": """
Go conventions:
- MixedCaps for exported names
- mixedCaps for unexported names
- Short variable names in limited scope
- Error handling with if err != nil
- Package names should be short and lowercase
- Use gofmt for formatting"""
        }
        
        return conventions.get(language, "Follow language-specific best practices and conventions.")
