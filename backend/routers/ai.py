import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIConnectionError, AsyncOpenAI, OpenAI, OpenAIError, RateLimitError
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..ai_client import get_async_openai_client, get_openai_client
from ..database import get_db
from .tasks import get_owned_task

router = APIRouter(prefix="/tasks", tags=["ai"])

CurrentUser = Annotated[models.User, Depends(auth.get_current_user)]
DB = Annotated[Session, Depends(get_db)]


@router.post("/{task_id}/ai-categorize")
def categorize_task_with_ai(
    task_id: int,
    current_user: CurrentUser,
    db: DB,
    client: Annotated[OpenAI, Depends(get_openai_client)],
):
    task = get_owned_task(db, task_id, current_user)

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
    except OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"AI Service Error: {str(e)}")


@router.post("/extract", response_model=schemas.Task, status_code=status.HTTP_201_CREATED)
async def extract_task_from_notes(
    notes: str,
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
                    {"role": "user", "content": notes},
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
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is currently overloaded or unreachable.",
                )
            await asyncio.sleep(1.5 * (attempt + 1))

        except OpenAIError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI Provider Error: {str(e)}",
            )

    raise HTTPException(status_code=500, detail="Extraction failed unexpectedly.")
