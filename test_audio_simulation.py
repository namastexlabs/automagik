#!/usr/bin/env python3
"""Simulate audio transcription workflow to demonstrate the pattern."""

import asyncio
import requests
import json
import os

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "simple"

def simulate_whisper_transcription(audio_file_path: str) -> str:
    """Simulate what Whisper transcription would return for the audio file."""
    
    # Since this is a Brazilian/Portuguese audio file about "Piraruvite de Pirarucu"
    # let's simulate what the transcription might look like
    simulated_transcriptions = {
        "portuguese": """
        Olá, hoje vamos falar sobre o Piraruvite de Pirarucu, um produto inovador 
        desenvolvido com tecnologia brasileira. O Pirarucu é um peixe amazônico 
        conhecido por sua alta qualidade nutricional e sabor único. Este produto 
        representa uma oportunidade de valorizar a biodiversidade amazônica 
        através de práticas sustentáveis de aquicultura.
        """,
        "english": """
        Hello, today we're going to talk about Piraruvite de Pirarucu, an innovative 
        product developed with Brazilian technology. The Pirarucu is an Amazonian fish 
        known for its high nutritional quality and unique flavor. This product represents 
        an opportunity to value Amazonian biodiversity through sustainable aquaculture practices.
        """
    }
    
    # Return Portuguese version (more likely for Brazilian audio)
    return simulated_transcriptions["portuguese"].strip()

def send_transcribed_text_to_agent(transcribed_text: str, session_name: str, language: str = "portuguese") -> dict:
    """Send transcribed text to the agent for analysis."""
    
    message_content = f"""Eu tenho um conteúdo de áudio que foi transcrito. Aqui está o que foi dito:

ÁUDIO TRANSCRITO:
"{transcribed_text}"

Por favor, analise este conteúdo de áudio e responda em português. 
Você pode fornecer informações sobre o tema mencionado?"""

    payload = {
        "message_content": message_content,
        "message_limit": 150,
        "user": {
            "phone_number": "+555197285829",
            "email": "test@example.com",
            "user_data": {
                "name": "Test User",
                "source": "api"
            }
        },
        "message_type": "text",
        "session_name": session_name,
        "preserve_system_prompt": False
    }
    
    try:
        response = requests.post(
            f"{API_URL}/agent/{AGENT_NAME}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def test_different_agents_with_audio(transcribed_text: str):
    """Test how different agents respond to transcribed audio."""
    
    agents_to_test = [
        {
            "name": "simple",
            "description": "Simple agent with multimodal capabilities"
        },
        {
            "name": "flashinho", 
            "description": "Educational assistant (Portuguese)"
        },
        {
            "name": "sofia",
            "description": "Professional assistant"
        },
        {
            "name": "summary",
            "description": "Summarization specialist"
        }
    ]
    
    results = []
    
    for agent in agents_to_test:
        print(f"\n🤖 Testing {agent['name']} agent...")
        print(f"   📋 {agent['description']}")
        
        # Customize message for each agent
        if agent['name'] == 'flashinho':
            message = f"""Oi! Você pode me ajudar a entender este áudio sobre Pirarucu?

ÁUDIO TRANSCRITO:
"{transcribed_text}"

Me explica sobre este tema de forma educativa?"""
        elif agent['name'] == 'summary':
            message = f"""Please provide a summary of this transcribed audio content:

TRANSCRIBED AUDIO:
"{transcribed_text}"

Create a comprehensive summary."""
        else:
            message = f"""I have transcribed audio content. Here's what was said:

TRANSCRIBED AUDIO:
"{transcribed_text}"

Can you analyze this content and provide insights?"""
        
        payload = {
            "message_content": message,
            "message_limit": 100,
            "user": {
                "phone_number": "+555197285829",
                "email": "test@example.com",
                "user_data": {
                    "name": "Test User",
                    "source": "api"
                }
            },
            "message_type": "text",
            "session_name": f"test-audio-{agent['name']}",
            "preserve_system_prompt": False
        }
        
        try:
            response = requests.post(
                f"{API_URL}/agent/{agent['name']}/run",
                json=payload,
                headers={
                    "x-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                agent_response = result.get('message', '')
                print(f"   ✅ Response: {agent_response[:150]}...")
                results.append({
                    "agent": agent['name'],
                    "success": True,
                    "response": agent_response[:200]
                })
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}...")
                results.append({
                    "agent": agent['name'],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                "agent": agent['name'],
                "success": False,
                "error": str(e)
            })
    
    return results

def main():
    """Main test function demonstrating audio → transcription → agent workflow."""
    print("🎵 AUDIO TRANSCRIPTION SIMULATION TEST")
    print("="*70)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    # Check if audio file exists
    if os.path.exists(audio_file):
        file_size = os.path.getsize(audio_file) / (1024*1024)
        print(f"📁 Audio file: {audio_file}")
        print(f"📏 File size: {file_size:.2f} MB")
    else:
        print(f"⚠️ Audio file not found: {audio_file}")
    
    print(f"\n🔄 Simulating Whisper transcription...")
    
    # Simulate transcription
    transcribed_text = simulate_whisper_transcription(audio_file)
    print(f"✅ Simulated transcription completed!")
    print(f"📝 Transcribed text: {transcribed_text[:100]}...")
    
    print(f"\n{'='*70}")
    print("🧪 TESTING MULTIPLE AGENTS WITH TRANSCRIBED AUDIO")
    print("="*70)
    
    # Test with multiple agents
    results = test_different_agents_with_audio(transcribed_text)
    
    print(f"\n{'='*70}")
    print("📊 RESULTS SUMMARY")
    print("="*70)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"✅ Successful agents: {len(successful)}/{len(results)}")
    print(f"❌ Failed agents: {len(failed)}/{len(results)}")
    
    if successful:
        print(f"\n🎯 SUCCESSFUL AGENTS:")
        for result in successful:
            print(f"   • {result['agent']}: Working ✅")
    
    if failed:
        print(f"\n💥 FAILED AGENTS:")
        for result in failed:
            print(f"   • {result['agent']}: {result['error']} ❌")
    
    print(f"\n{'='*70}")
    print("🔮 IMPLEMENTATION GUIDE")
    print("="*70)
    print("""
To implement real audio transcription:

1. 🔑 Configure API Keys:
   export OPENAI_API_KEY="your-openai-key"
   export GROQ_API_KEY="your-groq-key"  # Faster option

2. 📦 Install Dependencies:
   pip install openai groq

3. 🔄 Workflow Pattern:
   Audio File → Whisper API → Text → Agent → Response

4. ⚡ Performance Options:
   • Groq Whisper: Ultra-fast (recommended)
   • OpenAI Whisper: Standard speed
   • Local Whisper: No API calls needed

5. 🛠️ Integration Points:
   • Modify agent API to detect audio input
   • Add automatic transcription step
   • Pass transcribed text to agents
   • Maintain audio context in responses
""")

if __name__ == "__main__":
    main()