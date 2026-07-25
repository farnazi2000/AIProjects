"""Gemini-only LLM client for the incident investigation workflow."""

from __future__ import annotations
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()


class LLMClient:
    """Send investigation prompts to the Google Gemini API."""
    def complete(self, system: str, prompt: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured"
            )
        '''
        
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "The Gemini SDK is not installed in the Python environment running "
                "this application. Activate the project's virtual environment and run "
                "`python -m pip install -r requirements.txt`."
            ) from exc
        '''
        # This app calls the Gemini Developer API directly.  Explicitly opting out
        # of Vertex AI prevents inherited Google Cloud/OAuth settings from changing
        # the authentication mode.
        client = genai.Client(
            vertexai=False,
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1beta"),
        )
        response = client.interactions.create(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            input=f"{system}\n\n{prompt}",
        )
        if not response.output_text:
            raise RuntimeError("Gemini returned no text for this request.")
        return response.output_text
