"""
Task monitoring API endpoints.

This module provides API endpoints for monitoring Celery tasks.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel

from app.routers.auth import get_current_active_user
from app.models.user import User
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any = None
    error: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
) -> TaskStatusResponse:
    """Get the status of a Celery task."""
    from app.database import get_mongodb_database
    
    # Try to get from MongoDB first
    mongodb = get_mongodb_database()
    task_doc = await mongodb.celery_tasks.find_one({"task_id": task_id})
    
    if task_doc:
        return TaskStatusResponse(
            task_id=task_doc["task_id"],
            status=task_doc.get("status", "unknown"),
            result=task_doc.get("result"),
            error=task_doc.get("error"),
            created_at=task_doc.get("created_at").isoformat() if task_doc.get("created_at") else None,
            completed_at=task_doc.get("completed_at").isoformat() if task_doc.get("completed_at") else None
        )
    
    # Try to get from Celery result backend
    try:
        result = celery_app.AsyncResult(task_id)
        state = result.state
        
        return TaskStatusResponse(
            task_id=task_id,
            status=state,
            result=result.result if state == "SUCCESS" else None,
            error=str(result.info) if state == "FAILURE" else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )


@router.get("/user/{user_id}", response_model=List[TaskStatusResponse])
async def get_user_tasks(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    limit: int = 50
) -> List[TaskStatusResponse]:
    """Get all tasks for a specific user."""
    from app.database import get_mongodb_database
    
    mongodb = get_mongodb_database()
    tasks = []
    
    async for task_doc in mongodb.celery_tasks.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit):
        tasks.append(TaskStatusResponse(
            task_id=task_doc["task_id"],
            status=task_doc.get("status", "unknown"),
            result=task_doc.get("result"),
            error=task_doc.get("error"),
            created_at=task_doc.get("created_at").isoformat() if task_doc.get("created_at") else None,
            completed_at=task_doc.get("completed_at").isoformat() if task_doc.get("completed_at") else None
        ))
    
    return tasks


@router.post("/{task_id}/revoke")
async def revoke_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Revoke a running task."""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {"message": f"Task {task_id} revoked"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke task: {str(e)}"
        )


@router.get("")
async def list_tasks(
    current_user: User = Depends(get_current_active_user),
    status: str | None = None,
    limit: int = 50
) -> Dict[str, Any]:
    """List all tasks for the current user."""
    from app.database import get_mongodb_database
    from datetime import datetime
    
    mongodb = get_mongodb_database()
    
    query = {"user_id": str(current_user.id)}
    if status:
        query["status"] = status
    
    tasks = []
    async for task_doc in mongodb.celery_tasks.find(query).sort("created_at", -1).limit(limit):
        tasks.append({
            "task_id": task_doc["task_id"],
            "name": task_doc.get("name", "unknown"),
            "status": task_doc.get("status", "unknown"),
            "created_at": task_doc.get("created_at").isoformat() if task_doc.get("created_at") else None,
            "completed_at": task_doc.get("completed_at").isoformat() if task_doc.get("completed_at") else None,
            "error": task_doc.get("error")
        })
    
    # Get active tasks from Celery
    try:
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        
        for worker, task_list in active.items():
            for task in task_list:
                if task.get("id"):
                    # Check if this task belongs to the user
                    task_args = task.get("args", [])
                    if str(current_user.id) in str(task_args):
                        tasks.insert(0, {
                            "task_id": task["id"],
                            "name": task.get("name", "unknown"),
                            "status": "running",
                            "worker": worker,
                            "created_at": None,
                            "completed_at": None
                        })
    except Exception:
        pass  # Ignore Celery inspection errors
    
    return {
        "tasks": tasks,
        "count": len(tasks)
    }
