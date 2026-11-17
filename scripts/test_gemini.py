#!/usr/bin/env python3
import os
import sys

# Ensure backend in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.provider import ai_provider
from app.core.config import settings


def main():
    print("=" * 60)
    print("QueryMind AI — Google Gemini Connectivity Test")
    print("=" * 60)
    print(f"Provider:        {settings.LLM_PROVIDER}")
    print(f"Configured Model:{settings.GEMINI_MODEL}")
    print(f"Embedding Model: {settings.GEMINI_EMBEDDING_MODEL}")

    if not ai_provider.is_configured():
        print("\n[CONFIGURATION NOTICE]")
        print("GEMINI_API_KEY is currently empty or set to placeholder in backend/.env.")
        print("\nTo activate live Google Gemini API calls:")
        print("1. Get your API key from Google AI Studio: https://aistudio.google.com/app/apikey")
        print("2. Paste it in backend/.env:")
        print("   GEMINI_API_KEY=your_actual_key_here")
        print("3. Re-run this test script: .venv/bin/python scripts/test_gemini.py\n")
        return

    print("\nExecuting live API handshake with Google Gemini...")
    success, message, details = ai_provider.test_connectivity()
    if success:
        print(f"\n[SUCCESS] {message}")
        print(f"Latency:        {details.get('latency_ms')} ms")
        print(f"Model Verified: {details.get('model')}")
        print(f"Response:       {details.get('response_sample')}")
    else:
        print(f"\n[FAILED] {message}")
        if details:
            print(f"Error Details: {details.get('error')}")


if __name__ == "__main__":
    main()
