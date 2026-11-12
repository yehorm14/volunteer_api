import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIConnectionError, AsyncOpenAI, OpenAI, OpenAIError, RateLimitError

from .. import models, schemas
from ..ai_client import get_async_openai_client, get_openai_client
from ..deps import DB, CurrentUser, OwnedTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["ai"])

AI_UNAVAILABLE_DETAIL = "AI service is currently unavailable. Please try again later."


@router.post("/{task_id}/ai-categorize")
def categorize_task_with_ai(
    task: OwnedTask,  # resolved first: 404 for a missing/foreign task beats 503 for a missing key
    client: Annotated[OpenAI, Depends(get_openai_client)],
):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional organizer. Categorize this task into one word and give a 10-word explanation.",
                },
                {"role": "user", "content": f"Title: {task.title}\nDescription: {task.description}"},
            ],
            timeout=10.0,
        )
        return {"task_id": task.id, "ai_suggestion": response.choices[0].message.content}
    except OpenAIError:
        logger.exception("OpenAI categorize request failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=AI_UNAVAILABLE_DETAIL)


@router.post("/extract", response_model=schemas.Task, status_code=status.HTTP_201_CREATED)
async def extract_task_from_notes(
    payload: schemas.ExtractRequest,
    current_user: CurrentUser,
    db: DB,
    aclient: Annotated[AsyncOpenAI, Depends(get_async_openai_client)],
) -> models.Task:
    """Extract a structured task from free-text notes using structured output."""
    max_attempts = 2

    for attempt in range(max_attempts):
        try:
            response = await aclient.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional secretary. Extract a volunteer task from the notes. Keep the title concise.",
                    },
                    {"role": "user", "content": payload.notes},
                ],
                response_format=schemas.ParsedTask,
                timeout=15.0,
            )

            ai_message = response.choices[0].message

            if getattr(ai_message, "refusal", None):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"AI Refusal: {ai_message.refusal}",
                )

            extracted = ai_message.parsed
            if not extracted:
                raise HTTPException(status_code=500, detail="AI failed to parse content.")

            new_task = models.Task(
                title=extracted.title,
                description=extracted.description,
                owner_id=current_user.id,
                status="pending",
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            return new_task

        except (RateLimitError, APIConnectionError):
            if attempt == max_attempts - 1:
                logger.exception("OpenAI extract request failed after retries")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=AI_UNAVAILABLE_DETAIL)
            await asyncio.sleep(1.5 * (attempt + 1))

        except OpenAIError:
            logger.exception("OpenAI extract request failed")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=AI_UNAVAILABLE_DETAIL)

    raise HTTPException(status_code=500, detail="Extraction failed unexpectedly.")
