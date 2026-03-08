import json
import logging
import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    messages: list[dict]
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    system: str | None = None

class ChatResponse(BaseModel):
    response: str

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    settings = get_settings()
    try:
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        client = session.client("bedrock-runtime")
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": request.messages,
        }
        if request.system:
            payload["system"] = request.system
            
        body = json.dumps(payload)
        
        response = client.invoke_model(
            body=body,
            modelId=request.model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get("body").read())
        assistant_message = response_body.get("content", [{}])[0].get("text", "")
        
        return ChatResponse(response=assistant_message)
    except Exception as e:
        logger.exception("Error during chat endpoint execution")
        raise HTTPException(status_code=500, detail=str(e))