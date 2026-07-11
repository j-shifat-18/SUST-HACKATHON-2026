from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.openai_agent import openai_agent_service

router = APIRouter()

class CreateThreadResponse(BaseModel):
    thread_id: str
    message: str

class ChatRequest(BaseModel):
    thread_id: str = ""
    message: str

class ChatResponse(BaseModel):
    thread_id: str
    response: str

@router.post("/thread", response_model=CreateThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_new_thread():
    """
    Creates a new conversation thread for the OpenAI agent.
    Use this thread_id for subsequent /chat requests to maintain context.
    """
    try:
        thread_id = await openai_agent_service.create_thread()
        return {
            "thread_id": thread_id,
            "message": "Thread created successfully."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create thread: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(payload: ChatRequest):
    """
    Sends a message to the agent.
    If thread_id is not provided, a new thread is created automatically.
    """
    thread_id = payload.thread_id
    message = payload.message

    if not message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    try:
        # Create a thread if it wasn't provided
        if not thread_id:
            thread_id = await openai_agent_service.create_thread()

        # Run assistant on thread
        response = await openai_agent_service.run_chat(thread_id, message)
        
        return {
            "thread_id": thread_id,
            "response": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing agent run: {str(e)}"
        )
