"""Data models for Flashinho Pro agent."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ImageAnalysis(BaseModel):
    """Structured analysis of an image for educational content."""
    
    is_educational_problem: bool = Field(
        description="Whether the image contains an educational problem that needs solving"
    )
    
    subject: Optional[Literal[
        "mathematics", 
        "physics", 
        "chemistry", 
        "biology", 
        "history", 
        "geography", 
        "portuguese", 
        "english",
        "programming",
        "other"
    ]] = Field(
        None,
        description="The subject area of the problem, if educational"
    )
    
    problem_description: Optional[str] = Field(
        None,
        description="Brief description of what the problem is about"
    )
    
    confidence_level: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence level that this is an educational problem (0-1)"
    )
    
    suggested_approach: Optional[str] = Field(
        None,
        description="Suggested approach to solve this problem"
    )


class WorkflowStatus(BaseModel):
    """Status tracking for workflow execution."""
    
    workflow_id: str = Field(description="Unique identifier for the workflow run")
    status: Literal["started", "processing", "completed", "failed"] = Field(
        description="Current status of the workflow"
    )
    started_at: str = Field(description="ISO timestamp when workflow started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when workflow completed")
    duration_seconds: Optional[float] = Field(None, description="Total execution time in seconds")
    error: Optional[str] = Field(None, description="Error message if workflow failed")
    result_preview: Optional[str] = Field(None, description="Preview of the result")


class StepBreakdown(BaseModel):
    """Three-step breakdown structure for educational content."""
    
    step1_title: str = Field(default="Identificação e Compreensão")
    step1_content: str = Field(description="Content for step 1: problem identification")
    step1_emoji: str = Field(default="🔍")
    
    step2_title: str = Field(default="Desenvolvimento e Resolução")
    step2_content: str = Field(description="Content for step 2: solution development")
    step2_emoji: str = Field(default="✏️")
    
    step3_title: str = Field(default="Resposta Final e Verificação")
    step3_content: str = Field(description="Content for step 3: final answer and verification")
    step3_emoji: str = Field(default="✅")
    
    extra_tip: Optional[str] = Field(None, description="Additional tip or practical application")
    
    def format_response(self) -> str:
        """Format the breakdown into a nice response."""
        response = f"📚 **Análise Completa do Problema!**\n\n"
        response += f"**Passo 1: {self.step1_title}** {self.step1_emoji}\n"
        response += f"{self.step1_content}\n\n"
        response += f"**Passo 2: {self.step2_title}** {self.step2_emoji}\n"
        response += f"{self.step2_content}\n\n"
        response += f"**Passo 3: {self.step3_title}** {self.step3_emoji}\n"
        response += f"{self.step3_content}"
        
        if self.extra_tip:
            response += f"\n\n💡 **Dica Extra:** {self.extra_tip}"
            
        return response