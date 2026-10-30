# app.py
from fastapi import FastAPI
from pydantic import BaseModel

from mortgage_crew import run_mortgage_advisor

app = FastAPI(title="AI Mortgage Advisor Prototype")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """Main chat endpoint: receives a user message, returns the AI advisor's reply."""
    reply = run_mortgage_advisor(payload.message)
    return ChatResponse(reply=reply)


# For local dev: uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
