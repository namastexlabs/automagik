"""
Comprehensive Usage Calculator for Multimodal AI Operations

This module provides unified cost tracking across frameworks and content types,
addressing the PydanticAI bias and multimodal blindness in current tracking.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class MediaUsage:
    """Usage tracking for different media types."""
    text_tokens: int = 0
    image_tokens: int = 0  # Images typically equivalent to ~765 tokens each
    audio_seconds: float = 0.0  # Audio processing time
    video_seconds: float = 0.0  # Video processing time
    preprocessing_ms: float = 0.0  # Multimodal preprocessing overhead

@dataclass 
class UsageBreakdown:
    """Comprehensive usage breakdown for a single request."""
    framework: str
    model: str
    request_timestamp: str
    processing_time_ms: float
    
    # Token-based costs
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    
    # Multimodal usage
    media_usage: MediaUsage = None
    
    # Framework-specific data
    framework_events: List[Dict[str, Any]] = None
    
    # Content type attribution
    content_types: List[str] = None  # ['text', 'image', 'audio', 'video']
    
    def __post_init__(self):
        if self.media_usage is None:
            self.media_usage = MediaUsage()
        if self.framework_events is None:
            self.framework_events = []
        if self.content_types is None:
            self.content_types = []

class MediaTokenConfig:
    """Configuration for multimodal content token equivalents."""
    
    # Token equivalents for different media types
    MEDIA_TOKEN_EQUIVALENTS = {
        "image_token_equivalent": 765,  # GPT-4V: ~765 tokens per image
        "audio_tokens_per_second": 50,  # Estimated tokens per second of audio
        "video_frames_per_second": 1,   # Key frames extracted per second
        "video_tokens_per_frame": 765,  # Each frame = image token equivalent
    }

class UnifiedUsageCalculator:
    """Unified usage calculator that works across all frameworks and content types."""
    
    def __init__(self):
        self.media_config = MediaTokenConfig()
    
    def extract_pydantic_ai_usage(self, result: Any, model: str, processing_time_ms: float, multimodal_content: Optional[Dict[str, Any]] = None) -> UsageBreakdown:
        """Extract usage from PydanticAI result."""
        breakdown = UsageBreakdown(
            framework="pydantic_ai",
            model=model,
            request_timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time_ms
        )
        
        try:
            # Extract from PydanticAI's detailed usage tracking
            if hasattr(result, 'all_messages'):
                total_input = 0
                total_output = 0
                total_cached = 0
                
                for message in result.all_messages():
                    if hasattr(message, 'usage') and message.usage:
                        total_input += getattr(message.usage, 'request_tokens', 0) or 0
                        total_output += getattr(message.usage, 'response_tokens', 0) or 0
                        # PydanticAI specific: extract cache tokens from details
                        if hasattr(message.usage, 'details') and message.usage.details:
                            cache_creation = getattr(message.usage.details, 'cache_creation_input_tokens', 0) or 0
                            cache_read = getattr(message.usage.details, 'cache_read_input_tokens', 0) or 0
                            total_cached += cache_creation + cache_read
                
                breakdown.input_tokens = total_input
                breakdown.output_tokens = total_output
                breakdown.cached_tokens = total_cached
                breakdown.total_tokens = total_input + total_output
        
        except Exception as e:
            logger.warning(f"Error extracting PydanticAI usage: {e}")
        
        # Set content types dynamically based on multimodal content
        content_types = ["text"]
        if multimodal_content:
            if multimodal_content.get('images'):
                content_types.append("image")
            if multimodal_content.get('audio'):
                content_types.append("audio")
            if multimodal_content.get('videos'):
                content_types.append("video")
            if multimodal_content.get('documents'):
                content_types.append("document")
        
        breakdown.content_types = content_types
        
        return breakdown
    
    def extract_agno_usage(self, result: Any, model: str, processing_time_ms: float, 
                          multimodal_content: Optional[Dict[str, Any]] = None) -> UsageBreakdown:
        """Extract comprehensive usage from Agno result with multimodal awareness."""
        breakdown = UsageBreakdown(
            framework="agno",
            model=model,
            request_timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time_ms
        )
        
        # Initialize content types
        content_types = ["text"]
        
        try:
            # Extract basic token usage from Agno
            if hasattr(result, 'usage'):
                breakdown.input_tokens = getattr(result.usage, 'prompt_tokens', 0)
                breakdown.output_tokens = getattr(result.usage, 'completion_tokens', 0)
                breakdown.total_tokens = getattr(result.usage, 'total_tokens', 0)
            
            # Extract Agno-specific events for detailed tracking
            if hasattr(result, 'events') and result.events:
                breakdown.framework_events = [
                    {
                        "event": event.event,
                        "timestamp": getattr(event, 'timestamp', None),
                        "tool": getattr(event, 'tool', None),
                        "duration_ms": getattr(event, 'duration_ms', None)
                    }
                    for event in result.events
                ]
            
            # 🎯 MULTIMODAL USAGE TRACKING - Track media usage without pricing
            if multimodal_content:
                media_usage = MediaUsage()
                
                # Track image usage
                images = multimodal_content.get('images', [])
                if images:
                    content_types.append("image")
                    # Each image ~= 765 tokens equivalent
                    media_usage.image_tokens = len(images) * self.media_config.MEDIA_TOKEN_EQUIVALENTS["image_token_equivalent"]
                
                # Track audio usage
                audio_files = multimodal_content.get('audio', [])
                if audio_files:
                    content_types.append("audio")
                    # Estimate audio duration (would need actual duration in real implementation)
                    estimated_duration = len(audio_files) * 10.0  # Assume 10s per file
                    media_usage.audio_seconds = estimated_duration
                
                # Track video usage
                videos = multimodal_content.get('videos', [])
                if videos:
                    content_types.append("video")
                    # Estimate video duration
                    estimated_duration = len(videos) * 30.0  # Assume 30s per file
                    media_usage.video_seconds = estimated_duration
                
                # Preprocessing overhead
                media_usage.preprocessing_ms = processing_time_ms * 0.1  # 10% overhead for multimodal
                
                breakdown.media_usage = media_usage
            
        except Exception as e:
            logger.warning(f"Error extracting Agno usage: {e}")
        
        # Set content types used
        breakdown.content_types = content_types
        
        return breakdown
    
    def aggregate_session_usage(self, usage_breakdowns: List[UsageBreakdown]) -> Dict[str, Any]:
        """Aggregate usage across multiple requests in a session."""
        if not usage_breakdowns:
            return {}
        
        total_tokens = 0
        total_processing_time = 0.0
        framework_distribution = {}
        model_distribution = {}
        framework_model_combinations = {}
        content_type_distribution = {}
        model_content_attribution = {}
        
        for breakdown in usage_breakdowns:
            total_tokens += breakdown.total_tokens
            total_processing_time += breakdown.processing_time_ms
            
            # Framework distribution
            framework_distribution[breakdown.framework] = framework_distribution.get(breakdown.framework, 0) + 1
            
            # Model distribution
            model_distribution[breakdown.model] = model_distribution.get(breakdown.model, 0) + 1
            
            # Framework + Model combinations for detailed tracking
            combo_key = f"{breakdown.framework}:{breakdown.model}"
            if combo_key not in framework_model_combinations:
                framework_model_combinations[combo_key] = {
                    "requests": 0,
                    "total_tokens": 0,
                    "avg_processing_time": 0.0
                }
            framework_model_combinations[combo_key]["requests"] += 1
            framework_model_combinations[combo_key]["total_tokens"] += breakdown.total_tokens
            framework_model_combinations[combo_key]["avg_processing_time"] += breakdown.processing_time_ms
            
            # Content type distribution
            for content_type in breakdown.content_types:
                content_type_distribution[content_type] = content_type_distribution.get(content_type, 0) + 1
                
                # Model + Content type attribution
                model_content_key = f"{breakdown.model}:{content_type}"
                if model_content_key not in model_content_attribution:
                    model_content_attribution[model_content_key] = {
                        "requests": 0,
                        "tokens": 0
                    }
                model_content_attribution[model_content_key]["requests"] += 1
                model_content_attribution[model_content_key]["tokens"] += breakdown.total_tokens
        
        # Calculate averages for framework-model combinations
        for combo_data in framework_model_combinations.values():
            if combo_data["requests"] > 0:
                combo_data["avg_processing_time"] = combo_data["avg_processing_time"] / combo_data["requests"]
                combo_data["avg_tokens_per_request"] = combo_data["total_tokens"] / combo_data["requests"]
        
        return {
            "session_summary": {
                "total_requests": len(usage_breakdowns),
                "total_tokens": total_tokens,
                "total_processing_time_ms": total_processing_time,
                "average_tokens_per_request": round(total_tokens / len(usage_breakdowns), 2),
                "framework_distribution": framework_distribution,
                "model_distribution": model_distribution,
                "content_type_distribution": content_type_distribution,
                "framework_model_combinations": {
                    k: {
                        "requests": v["requests"],
                        "total_tokens": v["total_tokens"],
                        "avg_processing_time_ms": round(v["avg_processing_time"], 2),
                        "avg_tokens_per_request": round(v["avg_tokens_per_request"], 2)
                    } for k, v in framework_model_combinations.items()
                },
                "model_content_attribution": model_content_attribution,
            },
            "detailed_breakdowns": [asdict(breakdown) for breakdown in usage_breakdowns]
        }
    
    def create_legacy_compatible_usage(self, breakdown: UsageBreakdown) -> Dict[str, Any]:
        """Create usage data compatible with existing database schema."""
        return {
            "framework": breakdown.framework,
            "model": breakdown.model,
            "request_tokens": breakdown.input_tokens,
            "response_tokens": breakdown.output_tokens,
            "total_tokens": breakdown.total_tokens,
            "cached_tokens": breakdown.cached_tokens,
            "processing_time_ms": breakdown.processing_time_ms,
            "content_types": breakdown.content_types,
            # Enhanced multimodal data
            "media_usage": asdict(breakdown.media_usage) if breakdown.media_usage else None,
            "framework_events": breakdown.framework_events,
            "request_timestamp": breakdown.request_timestamp,
        }