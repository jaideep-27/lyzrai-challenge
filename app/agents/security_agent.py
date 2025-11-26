"""
Security Review Agent - Identifies security vulnerabilities in code changes
"""
from typing import List, Dict, Any
from app.agents.base_agent import BaseReviewAgent, AgentFinding


class SecurityAgent(BaseReviewAgent):
    """Agent specialized in finding security vulnerabilities"""
    
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            name="Security Agent",
            role="Security Vulnerability Analyst",
            goal="Identify security vulnerabilities, potential exploits, and unsafe coding practices"
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert security analyst specializing in code review. Your job is to identify security vulnerabilities in code changes.

Focus on detecting:
1. **Injection Vulnerabilities**: SQL injection, command injection, XSS, code injection
2. **Authentication/Authorization Issues**: Hardcoded credentials, weak auth, privilege escalation
3. **Data Exposure**: Sensitive data leaks, improper logging, PII handling
4. **Input Validation**: Missing validation, improper sanitization, buffer overflows
5. **Cryptographic Issues**: Weak encryption, hardcoded keys, insecure random
6. **Insecure Dependencies**: Known vulnerable patterns, unsafe imports
7. **Access Control**: Path traversal, IDOR, broken access control
8. **Security Misconfigurations**: Debug mode, insecure defaults

For each issue found:
- Clearly explain the vulnerability
- Rate severity (critical for exploitable issues, high for potential risks)
- Provide a specific fix recommendation
- Reference OWASP or CVE when applicable

Be thorough but avoid false positives. Only report genuine security concerns."""
    
    def analyze(self, code_context: Dict[str, Any]) -> List[AgentFinding]:
        """Analyze code for security vulnerabilities"""
        file_path = code_context.get("file_path", "unknown")
        
        system_prompt = self.get_system_prompt()
        analysis_prompt = self._create_analysis_prompt(code_context)
        
        # Add security-specific instructions
        full_prompt = f"""{system_prompt}

{analysis_prompt}

Focus specifically on SECURITY vulnerabilities. Categorize all findings as "security".
Common patterns to look for:
- eval(), exec(), or dynamic code execution
- SQL queries with string concatenation
- User input used in file paths
- Credentials or API keys in code
- Missing authentication checks
- Insecure deserialization
- Cross-site scripting vulnerabilities
- Insecure direct object references"""
        
        response = self.llm.generate(full_prompt)
        findings = self._parse_llm_response(response, file_path, "security")
        
        return findings
