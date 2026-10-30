# config.py
import os
from dotenv import load_dotenv
from crewai import LLM

# Load environment variables from .env
# .env example:
#   MISTRAL_API_KEY=your_key_here
#   MISTRAL_MODEL=mistral-large-latest
load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

if not MISTRAL_API_KEY:
    print("[config] WARNING: MISTRAL_API_KEY is not set. The LLM calls will fail until you add it to .env.")

# Configure the LLM used by all agents
# Adjust provider/model according to your crewai version and LLM provider.
mistral_llm = LLM(
    model=f"mistral/{MISTRAL_MODEL}",
    temperature=0.2,
    api_key=MISTRAL_API_KEY,
)
