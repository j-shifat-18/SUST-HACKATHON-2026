import logging
import asyncio
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger("uvicorn")

class OpenAIAgentService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client: Optional[AsyncOpenAI] = None
        self.assistant_id: Optional[str] = None
        
        if self.api_key:
            try:
                self.client = AsyncOpenAI(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize AsyncOpenAI client: {e}")
        else:
            logger.warning(
                "OPENAI_API_KEY is not configured. OpenAI Agent service will run in MOCK mode."
            )

    async def get_or_create_assistant(self) -> str:
        """
        Creates a default assistant or returns the cached assistant ID.
        """
        if not self.client:
            return "mock-assistant-id"
            
        if self.assistant_id:
            return self.assistant_id

        try:
            # We can create a lightweight assistant
            assistant = await self.client.beta.assistants.create(
                name="SUST Hackathon Co-pilot",
                instructions=(
                    "You are an AI Co-pilot for the SUST Hackathon 2026 application. "
                    "Help users plan their code, debug issues, and manage hackathon tasks."
                ),
                model="gpt-4o"  # default to a fast and reliable model
            )
            self.assistant_id = assistant.id
            logger.info(f"Created new OpenAI Assistant with ID: {self.assistant_id}")
            return self.assistant_id
        except Exception as e:
            logger.error(f"Error creating OpenAI Assistant: {e}")
            # Fallback to mock ID if OpenAI API calls fail (e.g. rate limit, credit limit)
            return "mock-assistant-id"

    async def create_thread(self) -> str:
        """Creates a new conversation thread."""
        if not self.client:
            return "mock-thread-id"
            
        try:
            thread = await self.client.beta.threads.create()
            return thread.id
        except Exception as e:
            logger.error(f"Error creating OpenAI thread: {e}")
            return "mock-thread-id"

    async def run_chat(self, thread_id: str, message: str) -> str:
        """
        Appends a message to a thread, runs the assistant, and returns the response.
        Handles mock fallback if keys are missing or invalid.
        """
        if not self.client or thread_id.startswith("mock-"):
            # Mock agent response simulator
            await asyncio.sleep(1) # simulate network latency
            return (
                f"[MOCK AGENT RESPONSE] Received your message: '{message}'.\n"
                f"To enable real responses, please populate 'OPENAI_API_KEY' in the backend/.env file."
            )

        try:
            # 1. Ensure assistant exists
            assistant_id = await self.get_or_create_assistant()
            if assistant_id == "mock-assistant-id":
                raise ValueError("Could not establish a real Assistant ID.")

            # 2. Add the user message to the thread
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )

            # 3. Create and poll the run until completion
            run = await self.client.beta.threads.runs.create_and_poll(
                thread_id=thread_id,
                assistant_id=assistant_id
            )

            if run.status == "completed":
                # 4. Fetch response messages
                messages = await self.client.beta.threads.messages.list(
                    thread_id=thread_id
                )
                
                # The response message is typically the latest one from the assistant
                for msg in messages.data:
                    if msg.role == "assistant":
                        # Return text content
                        content_blocks = msg.content
                        if content_blocks and len(content_blocks) > 0:
                            if hasattr(content_blocks[0], 'text'):
                                return content_blocks[0].text.value
                return "The agent ran successfully but did not return any text response."
            else:
                logger.error(f"Run ended with status: {run.status}")
                return f"Agent run failed or timed out with status: {run.status}"

        except Exception as e:
            logger.error(f"Error during OpenAI run_chat: {e}")
            return (
                f"Error communicating with OpenAI: {str(e)}. "
                "Ensure your API key is correct and has access to Assistants API."
            )

# Singleton service instance
openai_agent_service = OpenAIAgentService()
