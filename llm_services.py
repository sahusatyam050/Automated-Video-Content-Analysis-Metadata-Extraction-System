from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from typing import Optional

# 1. Define Request/Response Schemas (The "Contract" for other projects)
class TextRequest(BaseModel):
    text: str

class TranslationRequest(BaseModel):
    text: str
    target_lang: str = "English"

class AnalysisResponse(BaseModel):
    task: str
    result: str

# 2. Re-wrap your logic into a Service Class
class LLMService:
    def __init__(self, api_url: str):
        self.url = api_url

    def _call_llm(self, prompt: str, tokens: int = 256) -> str:
        payload = {
            "prompt": f"User: {prompt}\nAssistant:",
            "n_predict": tokens,
            "temperature": 0.7,
            "stop": ["User:"]
        }
        try:
            response = requests.post(self.url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("content", "").strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Backend Error: {str(e)}")

# 3. Initialize FastAPI and the Service
app = FastAPI(title="LLM Analysis Service", description="A shared API for text tasks")
# Update this IP to your actual local LLM endpoint
llm_client = LLMService(api_url="http://10.94.157.37:8080/completion")

# 4. Define API Endpoints
@app.post("/summary", response_model=AnalysisResponse)
async def summarize(request: TextRequest):
    prompt = f"Provide a concise summary of this text: {request.text}"
    result = llm_client._call_llm(prompt)
    return {"task": "summarization", "result": result}

@app.post("/sentiment", response_model=AnalysisResponse)
async def sentiment(request: TextRequest):
    prompt = f"Analyze the sentiment of this text. Reply with only one word (Positive, Negative, or Neutral): {request.text[:1000]}"
    result = llm_client._call_llm(prompt, tokens=10)
    return {"task": "sentiment", "result": result}

@app.post("/translate", response_model=AnalysisResponse)
async def translate(request: TranslationRequest):
    prompt = f"Translate the following text into {request.target_lang}: {request.text}"
    result = llm_client._call_llm(prompt, tokens=512)
    return {"task": "translation", "result": result}

# Health check for monitoring
@app.get("/health")
async def health():
    return {"status": "online"}