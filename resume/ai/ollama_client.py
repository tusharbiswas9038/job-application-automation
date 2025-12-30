# resume/ai/ollama_client.py
import logging
import requests
import json
from typing import Optional, Dict, List
import time

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for Ollama API to enhance resume content
    """
    
    def __init__(
        self,
        base_url: str = "http://217.142.188.41:11434",
        model: str = "jarvis-mid",
        timeout: int = 60
    ):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API endpoint
            model: Model to use (llama3.2:3b, mistral, etc.)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
    
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Generate text using Ollama
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Creativity (0.0-1.0)
            max_tokens: Max response length
        
        Returns:
            Generated text or None if failed
        """
        if not self.is_available():
            logger.error("Ollama is not available")
            return None
        
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Call API
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("message", {}).get("content", "").strip()
        
        except requests.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return None
    
    def enhance_bullet(
        self,
        bullet_text: str,
        job_title: str,
        keywords: List[str],
        temperature: float = 0.3
    ) -> Optional[str]:
        """
        Enhance a resume bullet point
        
        Args:
            bullet_text: Original bullet text
            job_title: Target job title
            keywords: Keywords to incorporate
            temperature: Lower = more consistent
        
        Returns:
            Enhanced bullet or None
        """
        system_prompt = """You are an expert resume writer and ATS optimization specialist.
Your job is to enhance resume bullet points to be:
1. ATS-friendly with relevant keywords
2. Achievement-focused with quantifiable results
3. Action-verb driven
4. Concise (under 25 words)
5. Natural and professional

DO NOT:
- Make up fake numbers or achievements
- Add information not implied in the original
- Use buzzwords or clichés
- Exceed 25 words"""
        
        keywords_str = ", ".join(keywords[:5])
        
        prompt = f"""Original bullet point:
{bullet_text}

Target role: {job_title}
Priority keywords to naturally incorporate: {keywords_str}

Enhance this bullet point while maintaining truthfulness. If the bullet already includes metrics, keep them. If not, you may suggest adding "[X]" as a placeholder for a metric.

Return ONLY the enhanced bullet point, nothing else."""
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=100
        )
    
    def generate_summary(
        self,
        experience_bullets: List[str],
        skills: List[str],
        job_title: str,
        keywords: List[str]
    ) -> Optional[str]:
        """
        Generate a professional summary
        
        Args:
            experience_bullets: Key experience points
            skills: Top skills
            job_title: Target job title
            keywords: Important keywords
        
        Returns:
            Generated summary (3-4 sentences)
        """
        system_prompt = """You are an expert resume writer. Create compelling professional summaries that:
1. Highlight relevant experience and skills
2. Incorporate target job keywords naturally
3. Are 3-4 sentences (60-80 words)
4. Use third-person perspective without pronouns
5. Focus on value proposition"""
        
        prompt = f"""Target Job: {job_title}

Key Experience:
{chr(10).join('- ' + b[:100] for b in experience_bullets[:5])}

Top Skills: {', '.join(skills[:10])}

Priority Keywords: {', '.join(keywords[:5])}

Write a professional summary that positions the candidate as an ideal fit for this {job_title} role."""
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=150
        )
    
    def suggest_bullet_improvements(
        self,
        bullet_text: str,
        missing_keywords: List[str]
    ) -> Dict[str, str]:
        """
        Suggest how to improve a bullet
        
        Returns:
            Dict with 'suggestion' and 'explanation'
        """
        prompt = f"""Bullet point: {bullet_text}

Missing important keywords: {', '.join(missing_keywords[:3])}

Provide:
1. A suggestion for how to incorporate these keywords naturally
2. Brief explanation of why

Format as JSON:
{{"suggestion": "improved text", "explanation": "why this works"}}"""
        
        response = self.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=200
        )
        
        if not response:
            return {}
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"suggestion": response}

