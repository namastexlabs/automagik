#!/usr/bin/env python3
"""Test keyword-based educational content detection."""

def test_educational_detection(user_message: str) -> tuple[bool, str]:
    """Test the keyword detection logic."""
    
    # Detect educational context from user message
    educational_keywords = {
        "matemática": ["equação", "resolver", "matemática", "cálculo", "álgebra", "geometria"],
        "física": ["física", "cinemática", "força", "energia", "movimento"],
        "química": ["química", "reação", "elemento", "molécula", "átomo"],
        "biologia": ["biologia", "célula", "DNA", "fotossíntese", "evolução"],
        "história": ["história", "guerra", "império", "revolução", "século"],
        "geografia": ["geografia", "mapa", "país", "clima", "relevo"],
        "português": ["português", "texto", "gramática", "literatura"],
        "inglês": ["inglês", "english", "tradução", "vocabulário"],
        "educacional": ["exercício", "questão", "problema", "dúvida", "estudar", "prova", "vestibular"]
    }
    
    detected_subject = "geral"
    user_text = user_message.lower()
    
    # Check for subject-specific keywords
    for subject, keywords in educational_keywords.items():
        if any(keyword in user_text for keyword in keywords):
            detected_subject = subject
            print(f"Detected educational subject: {subject}")
            break
    
    # If we have any educational context, consider it a student problem
    is_educational = detected_subject != "geral" or any(
        keyword in user_text for keywords in educational_keywords.values() for keyword in keywords
    )
    
    if is_educational:
        context = f"educational content detected: {detected_subject} problem"
        print(f"Student problem detected: {context}")
        return True, context
    else:
        print("No educational context detected")
        return False, ""


def main():
    """Test the detection logic."""
    test_messages = [
        "[Cezar]: Preciso resolver essa equação de segundo grau",
        "[Cezar]: Me ajuda com esse problema de cinemática", 
        "[Cezar]: Não entendi essa reação química",
        "[Cezar]: Preciso de ajuda com esse exercício",
        "[Cezar]: Como vai o dia hoje?",  # Non-educational
        "[Cezar]: Olha essa questão de matemática que não consigo resolver"
    ]
    
    print("🧪 TESTING KEYWORD-BASED DETECTION")
    print("="*50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message}")
        is_detected, context = test_educational_detection(message)
        print(f"Result: {'✅ DETECTED' if is_detected else '❌ NOT DETECTED'}")
        if context:
            print(f"Context: {context}")


if __name__ == "__main__":
    main()