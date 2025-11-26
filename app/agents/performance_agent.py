"""
Performance Review Agent - Identifies performance issues in code changes
"""
from typing import List, Dict, Any
from app.agents.base_agent import BaseReviewAgent, AgentFinding


class PerformanceAgent(BaseReviewAgent):
    """Agent specialized in finding performance issues"""
    
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            name="Performance Agent",
            role="Performance Optimization Specialist",
            goal="Identify performance bottlenecks, inefficient algorithms, and resource waste"
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert performance engineer specializing in code optimization. Your job is to identify performance issues in code changes.

Focus on detecting:
1. **Algorithm Complexity**: O(n²) or worse when better alternatives exist, inefficient sorting/searching
2. **Memory Issues**: Memory leaks, excessive allocations, large object retention
3. **I/O Inefficiencies**: Synchronous blocking, missing caching, N+1 queries
4. **Resource Management**: Unclosed connections, missing connection pooling
5. **Loop Inefficiencies**: Redundant computations, inefficient iterations
6. **Data Structure Misuse**: Wrong data structures for the use case
7. **Caching Opportunities**: Missing memoization, repeated expensive operations
8. **Concurrency Issues**: Thread safety problems, deadlock risks, race conditions
9. **Database Performance**: Missing indexes, inefficient queries, bulk operation opportunities
10. **Network Optimization**: Excessive API calls, missing batching

For each issue:
- Explain the performance impact
- Provide Big-O analysis when relevant
- Suggest specific optimizations
- Estimate potential improvement

Be practical - focus on issues that have real-world impact."""
    
    def analyze(self, code_context: Dict[str, Any]) -> List[AgentFinding]:
        """Analyze code for performance issues"""
        file_path = code_context.get("file_path", "unknown")
        language = code_context.get("language", "unknown")
        
        system_prompt = self.get_system_prompt()
        analysis_prompt = self._create_analysis_prompt(code_context)
        
        # Add performance-specific instructions
        language_specific = self._get_language_specific_hints(language)
        
        full_prompt = f"""{system_prompt}

{analysis_prompt}

Focus specifically on PERFORMANCE issues. Categorize all findings as "performance".

{language_specific}

Common patterns to look for:
- Nested loops that could be optimized
- Database queries inside loops (N+1 problem)
- Large data structures copied unnecessarily
- Missing async/await for I/O operations
- Repeated calculations that could be cached
- Inefficient string concatenation in loops"""
        
        response = self.llm.generate(full_prompt)
        findings = self._parse_llm_response(response, file_path, "performance")
        
        return findings
    
    def _get_language_specific_hints(self, language: str) -> str:
        """Get language-specific performance hints"""
        hints = {
            "python": """
Python-specific patterns:
- List comprehensions vs loops
- Generator expressions for large datasets
- Using sets/dicts for O(1) lookups
- Avoiding global variable access in loops
- Using `__slots__` for memory optimization
- asyncio for I/O-bound operations""",
            
            "javascript": """
JavaScript-specific patterns:
- Avoid DOM manipulation in loops
- Use Map/Set for frequent lookups
- Consider Web Workers for CPU-intensive tasks
- Debounce/throttle event handlers
- Lazy loading and code splitting
- Avoid memory leaks from closures""",
            
            "typescript": """
TypeScript-specific patterns:
- Same as JavaScript optimizations
- Efficient type guards
- Avoid excessive type assertions
- Consider readonly for immutability""",
            
            "java": """
Java-specific patterns:
- StringBuilder vs String concatenation
- Proper collection sizing (ArrayList initial capacity)
- Stream API for parallel processing
- Connection pooling for databases
- Avoid boxing/unboxing overhead
- Use primitives over wrapper classes when possible""",
            
            "go": """
Go-specific patterns:
- Avoid allocations in hot paths
- Use sync.Pool for frequently allocated objects
- Proper goroutine management
- Channel buffer sizing
- Use pointers for large structs"""
        }
        
        return hints.get(language, "")
