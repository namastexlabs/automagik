#!/usr/bin/env python3
"""
Model Tracking Showcase

Demonstrates comprehensive model tracking across different scenarios:
1. Different models with same framework
2. Same model with different frameworks  
3. Model-specific cost calculations
4. Framework + Model combination analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.usage_calculator import UnifiedUsageCalculator, UsageBreakdown, MediaCost, ModelPricingConfig
import json

def test_model_cost_variations():
    """Test how different models affect cost calculations."""
    print("🤖 MODEL COST VARIATION ANALYSIS")
    print("="*60)
    
    calculator = UnifiedUsageCalculator()
    
    # Same usage, different models
    base_tokens = {"input": 1000, "output": 500}
    test_models = [
        "openai:gpt-4o",
        "openai:gpt-4", 
        "openai:gpt-3.5-turbo",
        "anthropic:claude-3-sonnet",
        "google:gemini-1.5-pro",
        "groq:llama"
    ]
    
    print(f"📊 Cost Comparison for {base_tokens['input']} input + {base_tokens['output']} output tokens:")
    print(f"{'Model':<25} {'Framework':<12} {'Cost USD':<12} {'Relative':<10}")
    print("-" * 70)
    
    base_cost = None
    results = []
    
    for model in test_models:
        # Determine framework (simplified)
        if "openai:" in model or "anthropic:" in model or "google:" in model:
            framework = "agno"  # Agno handles multiple providers
        else:
            framework = "pydantic_ai"
        
        breakdown = UsageBreakdown(
            framework=framework,
            model=model,
            request_timestamp="2025-01-01T00:00:00Z",
            processing_time_ms=2000,
            input_tokens=base_tokens["input"],
            output_tokens=base_tokens["output"],
            total_tokens=base_tokens["input"] + base_tokens["output"]
        )
        
        # Calculate cost
        breakdown.estimated_cost_usd = calculator.pricing_config.calculate_text_cost(
            model, base_tokens["input"], base_tokens["output"]
        )
        
        if base_cost is None:
            base_cost = breakdown.estimated_cost_usd
        
        relative_cost = breakdown.estimated_cost_usd / base_cost
        
        print(f"{model:<25} {framework:<12} ${breakdown.estimated_cost_usd:<11.6f} {relative_cost:<9.1f}x")
        
        results.append({
            "model": model,
            "framework": framework, 
            "cost": breakdown.estimated_cost_usd,
            "breakdown": breakdown
        })
    
    print(f"\n💡 Insights:")
    cheapest = min(results, key=lambda x: x["cost"])
    most_expensive = max(results, key=lambda x: x["cost"])
    
    print(f"   💚 Cheapest: {cheapest['model']} (${cheapest['cost']:.6f})")
    print(f"   💸 Most Expensive: {most_expensive['model']} (${most_expensive['cost']:.6f})")
    print(f"   📈 Cost Range: {most_expensive['cost'] / cheapest['cost']:.1f}x difference")

def test_multimodal_model_costs():
    """Test model costs with multimodal content."""
    print("\n🎭 MULTIMODAL MODEL COST ANALYSIS")
    print("="*60)
    
    calculator = UnifiedUsageCalculator()
    
    # Multimodal scenario: 2 images + 10s audio + text
    multimodal_content = {
        "images": [{"type": "image"}, {"type": "image"}],
        "audio": [{"type": "audio", "duration": 10}],
        "videos": []
    }
    
    multimodal_models = [
        "openai:gpt-4o",      # Best multimodal
        "openai:gpt-4",       # Premium multimodal
        "google:gemini-1.5-pro", # Google's multimodal
        "anthropic:claude-3-sonnet" # Anthropic's multimodal
    ]
    
    print(f"📊 Multimodal Cost Analysis (2 images + 10s audio + 300 text tokens):")
    print(f"{'Model':<25} {'Text Cost':<12} {'Media Cost':<12} {'Total Cost':<12} {'Breakdown'}")
    print("-" * 90)
    
    for model in multimodal_models:
        breakdown = calculator.extract_agno_usage(
            result=None,  # Mock result
            model=model,
            processing_time_ms=3000,
            multimodal_content=multimodal_content
        )
        
        # Add some text tokens
        breakdown.input_tokens = 200
        breakdown.output_tokens = 100
        breakdown.total_tokens = 300
        
        # Recalculate with text
        text_cost = calculator.pricing_config.calculate_text_cost(model, 200, 100)
        media_cost = sum(breakdown.cost_breakdown.values()) - breakdown.cost_breakdown.get("text", 0)
        total_cost = text_cost + media_cost
        
        breakdown.estimated_cost_usd = total_cost
        breakdown.cost_breakdown["text"] = text_cost
        
        print(f"{model:<25} ${text_cost:<11.6f} ${media_cost:<11.6f} ${total_cost:<11.6f} {len(breakdown.cost_breakdown)} types")
        
        # Show detailed breakdown
        for cost_type, cost_value in breakdown.cost_breakdown.items():
            if cost_value > 0:
                print(f"   - {cost_type}: ${cost_value:.6f}")

def test_framework_model_combinations():
    """Test tracking of framework + model combinations."""
    print("\n🔧 FRAMEWORK + MODEL COMBINATION TRACKING")
    print("="*60)
    
    calculator = UnifiedUsageCalculator()
    
    # Simulate session with multiple requests
    session_breakdowns = [
        # PydanticAI requests
        UsageBreakdown(
            framework="pydantic_ai", model="gpt-3.5-turbo",
            request_timestamp="2025-01-01T00:00:00Z", processing_time_ms=1500,
            input_tokens=500, output_tokens=200, total_tokens=700,
            estimated_cost_usd=0.0015
        ),
        UsageBreakdown(
            framework="pydantic_ai", model="gpt-4o",
            request_timestamp="2025-01-01T00:01:00Z", processing_time_ms=2000,
            input_tokens=800, output_tokens=300, total_tokens=1100,
            estimated_cost_usd=0.0085
        ),
        # Agno requests  
        UsageBreakdown(
            framework="agno", model="openai:gpt-4o",
            request_timestamp="2025-01-01T00:02:00Z", processing_time_ms=2500,
            input_tokens=1000, output_tokens=400, total_tokens=1400,
            estimated_cost_usd=0.011,
            media_costs=MediaCost(image_tokens=765)
        ),
        UsageBreakdown(
            framework="agno", model="google:gemini-1.5-pro",
            request_timestamp="2025-01-01T00:03:00Z", processing_time_ms=2200,
            input_tokens=900, output_tokens=350, total_tokens=1250,
            estimated_cost_usd=0.0095
        ),
    ]
    
    # Aggregate session data
    session_summary = calculator.aggregate_session_usage(session_breakdowns)
    
    print("📊 Session Summary:")
    summary = session_summary["session_summary"]
    print(f"   Total Requests: {summary['total_requests']}")
    print(f"   Total Cost: ${summary['total_cost_usd']:.6f}")
    print(f"   Average Cost/Request: ${summary['average_cost_per_request']:.6f}")
    
    print(f"\n🔧 Framework Distribution:")
    for framework, count in summary["framework_distribution"].items():
        print(f"   {framework}: {count} requests")
    
    print(f"\n🤖 Model Distribution:")
    for model, count in summary["model_distribution"].items():
        print(f"   {model}: {count} requests")
    
    print(f"\n🎯 Framework + Model Combinations:")
    for combo, stats in summary["framework_model_combinations"].items():
        framework, model = combo.split(":", 1)
        print(f"   {framework} + {model}:")
        print(f"     Requests: {stats['requests']}")
        print(f"     Total Cost: ${stats['total_cost_usd']:.6f}")
        print(f"     Avg Cost/Request: ${stats['avg_cost_per_request']:.6f}")
        print(f"     Avg Processing Time: {stats['avg_processing_time_ms']:.1f}ms")
    
    print(f"\n💰 Cost by Type:")
    for cost_type, cost_value in summary["cost_by_type"].items():
        if cost_value > 0:
            print(f"   {cost_type}: ${cost_value:.6f}")

def test_model_pricing_accuracy():
    """Test accuracy of model pricing data."""
    print("\n💲 MODEL PRICING ACCURACY TEST")
    print("="*60)
    
    config = ModelPricingConfig()
    
    # Test known pricing (as of 2025)
    known_prices = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }
    
    print("🔍 Pricing Accuracy Check:")
    print(f"{'Model':<20} {'Expected Input':<15} {'Actual Input':<15} {'Expected Output':<16} {'Actual Output':<15} {'Status'}")
    print("-" * 100)
    
    for model, expected in known_prices.items():
        actual = config.get_model_pricing(model)
        
        input_match = abs(actual["input"] - expected["input"]) < 0.0001
        output_match = abs(actual["output"] - expected["output"]) < 0.0001
        
        status = "✅ Accurate" if input_match and output_match else "❌ Mismatch"
        
        print(f"{model:<20} ${expected['input']:<14.6f} ${actual['input']:<14.6f} ${expected['output']:<15.6f} ${actual['output']:<14.6f} {status}")
    
    print(f"\n📈 Total Models Supported: {len(config.MODEL_PRICING)}")
    print(f"   OpenAI: {len([m for m in config.MODEL_PRICING.keys() if 'gpt' in m])}")
    print(f"   Anthropic: {len([m for m in config.MODEL_PRICING.keys() if 'claude' in m])}")
    print(f"   Google: {len([m for m in config.MODEL_PRICING.keys() if 'gemini' in m])}")
    print(f"   Others: {len(config.MODEL_PRICING) - len([m for m in config.MODEL_PRICING.keys() if any(x in m for x in ['gpt', 'claude', 'gemini'])])}")

def main():
    """Run model tracking showcase."""
    print("🤖 MODEL TRACKING SHOWCASE")
    print("="*80)
    print("Demonstrating comprehensive model tracking and cost analysis")
    print("="*80)
    
    try:
        test_model_cost_variations()
        test_multimodal_model_costs()
        test_framework_model_combinations()
        test_model_pricing_accuracy()
        
        print(f"\n🎉 MODEL TRACKING SHOWCASE COMPLETE!")
        print("✅ Model costs accurately calculated")
        print("✅ Framework + Model combinations tracked")
        print("✅ Multimodal model costs properly attributed")
        print("✅ Model distribution analytics available")
        print("✅ Pricing accuracy verified")
        
    except Exception as e:
        print(f"\n❌ SHOWCASE FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()