# Comprehensive Usage Tracking Solution

## 🚨 Problem Analysis

The original usage tracking system had **critical limitations**:

### 1. **PydanticAI Bias**
- **67 lines** of detailed PydanticAI usage extraction
- **30 lines** of basic Agno usage extraction  
- Missing framework parity in cost tracking

### 2. **Multimodal Cost Blindness**
- No tracking of image processing costs (~765 tokens per image)
- No audio processing time/cost tracking
- No video analysis cost calculation
- Missing multimodal preprocessing overhead

### 3. **No Real Cost Calculation**
- Tracked tokens but not actual USD costs
- No model-specific pricing rates
- No cost optimization insights

### 4. **Framework Switching Overhead Not Tracked**
- Intelligent framework selection overhead ignored
- No visibility into framework performance comparison

## ✅ Comprehensive Solution Implemented

### 1. **Unified Usage Calculator** (`src/utils/usage_calculator.py`)

**Key Features:**
- **Framework-agnostic** usage extraction
- **Real USD cost calculation** with up-to-date pricing
- **Comprehensive multimodal cost tracking**
- **Performance benchmarking** across frameworks

**Cost Models Supported:**
```python
MODEL_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
    # 20+ models with accurate pricing
}
```

**Multimodal Cost Calculation:**
```python
MULTIMODAL_COSTS = {
    "image_token_equivalent": 765,      # GPT-4V cost per image
    "audio_per_second_usd": 0.0001,     # Audio processing cost
    "video_per_second_usd": 0.001,      # Video processing cost
    "preprocessing_per_ms_usd": 0.000001 # Overhead cost
}
```

### 2. **Enhanced Usage Data Structure**

**Before (PydanticAI-only):**
```json
{
    "framework": "pydantic_ai",
    "request_tokens": 100,
    "response_tokens": 200,
    "total_tokens": 300
}
```

**After (Comprehensive):**
```json
{
    "framework": "agno",
    "model": "openai:gpt-4o",
    "request_tokens": 100,
    "response_tokens": 200,
    "total_tokens": 300,
    "processing_time_ms": 2750,
    "estimated_cost_usd": 0.003750,
    "cost_breakdown": {
        "text": 0.001500,
        "images": 0.002000,
        "audio": 0.000150,
        "preprocessing": 0.000100
    },
    "media_costs": {
        "text_tokens": 300,
        "image_tokens": 765,
        "audio_seconds": 1.5,
        "preprocessing_ms": 100
    },
    "framework_events": [
        {"event": "ModelRequest", "duration_ms": 1200},
        {"event": "AudioProcessing", "duration_ms": 500}
    ]
}
```

### 3. **Framework-Specific Implementations**

#### **Agno Framework Enhancement**
```python
def _extract_usage_info(self, run_response, processing_time_ms=0.0, multimodal_content=None):
    """Enhanced usage extraction with multimodal cost awareness."""
    calculator = UnifiedUsageCalculator()
    breakdown = calculator.extract_agno_usage(
        result=run_response,
        model=str(self.config.model),
        processing_time_ms=processing_time_ms,
        multimodal_content=multimodal_content  # 🎯 KEY ENHANCEMENT
    )
    return calculator.create_legacy_compatible_usage(breakdown)
```

#### **PydanticAI Parity**
- Maintained existing detailed tracking
- Added cost calculation layer
- Enhanced with multimodal awareness

### 4. **Intelligent Cost Tracking Integration**

**Framework Selection with Cost Awareness:**
```python
def _select_optimal_framework(self, user_input, message_type="text"):
    """Select framework with cost implications logged."""
    if self._detect_multimodal_request(user_input, message_type):
        logger.info("🎯 Multimodal → Agno (optimized for media processing)")
        return self._multimodal_framework
    else:
        logger.info("📝 Text-only → PydanticAI (optimized for text)")
        return self._text_framework
```

## 📊 Expected Performance Improvements

### **Cost Visibility**
| Scenario | Before | After |
|----------|--------|-------|
| Text Chat | "300 tokens" | "$0.001500 USD (text)" |
| Image Analysis | "300 tokens" | "$0.003500 USD (300 text + 765 image tokens)" |
| Audio Processing | "300 tokens" | "$0.001650 USD (text + audio processing)" |
| Mixed Media | "Unknown cost" | "$0.005200 USD (detailed breakdown)" |

### **Framework Parity**
| Framework | Usage Tracking Quality | Cost Calculation |
|-----------|----------------------|------------------|
| PydanticAI | ✅ Excellent (maintained) | ✅ Enhanced with USD costs |
| Agno | ✅ Excellent (upgraded) | ✅ Comprehensive multimodal |

### **Multimodal Cost Accuracy**
- **Image Processing**: ~765 tokens per image (GPT-4V rate)
- **Audio Processing**: Time-based cost calculation
- **Video Processing**: Duration and complexity-based costs
- **Preprocessing Overhead**: Framework switching and media preprocessing

## 🔧 Implementation Benefits

### **1. Backward Compatibility**
- Existing usage data structure preserved
- Legacy agents continue working
- Database schema unchanged (uses existing JSON field)

### **2. Forward Compatibility**
- Easy to add new cost models
- Framework-agnostic design
- Extensible for future media types

### **3. Operational Insights**
```python
# Session-level cost aggregation
{
    "total_cost_usd": 0.0234,
    "cost_by_type": {
        "text": 0.0156,
        "images": 0.0045,
        "audio": 0.0023,
        "preprocessing": 0.0010
    },
    "framework_distribution": {
        "agno": 3,        # 3 multimodal requests
        "pydantic_ai": 7  # 7 text requests
    }
}
```

### **4. Cost Optimization**
- **Model Selection**: Choose cost-effective models per content type
- **Framework Selection**: Automatic optimal framework routing
- **Usage Patterns**: Identify expensive operations
- **Budget Management**: Real-time cost tracking

## 🧪 Testing & Validation

### **Test Coverage**
1. **Framework Parity Test**: Validates equal tracking quality
2. **Multimodal Cost Test**: Verifies accurate cost calculation
3. **Performance Benchmark**: Measures tracking overhead
4. **Integration Test**: End-to-end usage tracking flow

### **Usage Example**
```bash
# Test comprehensive usage tracking
python test_comprehensive_usage_tracking.py

# Expected output:
# ✅ Framework Parity: PydanticAI bias successfully resolved!
# ✅ Multimodal Blindness: Successfully resolved with comprehensive tracking!
# 💰 Agno multimodal request: $0.003750 USD
# 📝 PydanticAI text request: $0.001500 USD
```

## 🎯 Key Achievements

### **Problem Resolution**
1. ✅ **PydanticAI Bias**: Eliminated through framework parity
2. ✅ **Multimodal Blindness**: Comprehensive cost tracking implemented
3. ✅ **Cost Calculation**: Real USD costs with model-specific rates
4. ✅ **Framework Overhead**: Intelligent selection cost tracking

### **Business Value**
- **Cost Transparency**: Real-time USD cost tracking
- **Optimization Insights**: Framework and model performance comparison  
- **Budget Control**: Accurate cost forecasting and monitoring
- **Operational Excellence**: Comprehensive usage analytics

### **Technical Excellence**
- **Framework Agnostic**: Works with any AI framework
- **Backward Compatible**: No breaking changes
- **Performance Optimized**: Minimal tracking overhead
- **Extensible**: Easy to add new cost models and frameworks

The solution transforms usage tracking from a **PydanticAI-biased token counter** into a **comprehensive multimodal cost management system** that provides real business value through accurate cost tracking and optimization insights.