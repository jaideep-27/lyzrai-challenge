"""
Logic Review Agent - Identifies logical errors and bugs in code changes
"""
from typing import List, Dict, Any
from app.agents.base_agent import BaseReviewAgent, AgentFinding


class LogicAgent(BaseReviewAgent):
    """Agent specialized in finding logical errors and bugs"""
    
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            name="Logic Agent",
            role="Logic & Bug Detection Specialist",
            goal="Identify logical errors, potential bugs, edge cases, and incorrect implementations"
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert software engineer specializing in finding bugs and logical errors. Your job is to identify logical issues in code changes.

Focus on detecting:
1. **Logical Errors**: Incorrect conditions, wrong operators, flawed algorithms
2. **Edge Cases**: Unhandled null/undefined, empty collections, boundary conditions
3. **Off-by-One Errors**: Array bounds, loop conditions, range calculations
4. **Race Conditions**: Concurrent access issues, state management problems
5. **Incorrect Assumptions**: Wrong data type assumptions, API misuse
6. **Missing Validations**: Unchecked inputs, unverified preconditions
7. **Control Flow Issues**: Unreachable code, infinite loops, missing breaks
8. **State Management**: Incorrect state transitions, missing state updates
9. **Error Propagation**: Lost errors, incorrect error handling flow
10. **Business Logic**: Incorrect calculations, wrong conditions for business rules

For each issue:
- Explain the logical flaw clearly
- Provide a concrete example of how it fails
- Suggest the correct implementation
- Rate severity based on potential impact

Be precise - identify specific bugs that could cause runtime failures."""
    
    def analyze(self, code_context: Dict[str, Any]) -> List[AgentFinding]:
        """Analyze code for logical errors"""
        file_path = code_context.get("file_path", "unknown")
        
        system_prompt = self.get_system_prompt()
        analysis_prompt = self._create_analysis_prompt(code_context)
        
        full_prompt = f"""{system_prompt}

{analysis_prompt}

Focus specifically on LOGIC issues and potential BUGS. Categorize all findings as "logic".

Common patterns to look for:
- Wrong comparison operators (== vs ===, < vs <=)
- Incorrect boolean logic (AND vs OR, negation errors)
- Unhandled null/undefined values
- Array index out of bounds
- Division by zero possibilities
- Incorrect loop termination conditions
- Missing return statements
- Uninitialized variables
- Type coercion issues
- Async/await missing or misused
- Promise rejection not handled
- Incorrect error propagation"""
        
        response = self.llm.generate(full_prompt)
        findings = self._parse_llm_response(response, file_path, "logic")
        
        return findings
