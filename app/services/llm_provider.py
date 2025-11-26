"""
LLM Provider - Google Gemini integration for agents
"""
import google.generativeai as genai
from typing import Optional
import os


class GeminiLLM:
    """Wrapper for Google Gemini LLM"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.3
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        self.temperature = temperature
        
        if not self.api_key:
            raise ValueError("Google API key not provided")
        
        genai.configure(api_key=self.api_key)
        
        self.generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
        )
    
    def generate(self, prompt: str) -> str:
        """Generate a response from the LLM"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"LLM generation failed: {str(e)}")
    
    def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """Generate with system and user prompts"""
        full_prompt = f"""System Instructions:
{system_prompt}

User Request:
{user_prompt}"""
        return self.generate(full_prompt)


def get_llm(
    api_key: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    temperature: float = 0.3
) -> GeminiLLM:
    """Factory function to get LLM instance"""
    return GeminiLLM(api_key=api_key, model=model, temperature=temperature)
