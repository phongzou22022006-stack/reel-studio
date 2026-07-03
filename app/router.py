"""
API router for FastAPI endpoints.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional

from app.models.schema import (
    TaskCreateRequest,
    TaskResumeRequest,
    TaskUpdateRequest,
    VideoParams,
)
from app.services import task as tm
from app.services import templating, state as sm


api_router = APIRouter()


@api_router.post("/tasks/create")
async def create_task(request: TaskCreateRequest):
    """Create a new video generation task."""
    params = VideoParams(
        video_subject=request.video_subject,
        video_script=request.video_script or "",
        script_template=request.script_template or "default",
        prompt_template=request.prompt_template or "default",
        style_config=request.style_config or "",
        video_aspect=request.video_aspect,
        video_count=request.video_count,
        stop_at=request.stop_at,
    )
    
    import uuid
    task_id = str(uuid.uuid4())[:8]
    
    # Start task in background (simplified - in production use background tasks)
    result = tm.start(task_id=task_id, params=params, stop_at=request.stop_at)
    
    if not result:
        raise HTTPException(status_code=500, detail="Task failed to start")
    
    return {
        "task_id": task_id,
        "status": "processing",
        "result": result,
    }


@api_router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, request: TaskResumeRequest):
    """Resume a paused task."""
    result = tm.resume_task(task_id=task_id, images=request.images)
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found or resume failed")
    
    return {
        "task_id": task_id,
        "status": "complete",
        "result": result,
    }


@api_router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status and outputs."""
    task_data = sm.state.get_task(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_data


@api_router.get("/tasks")
async def list_tasks(limit: int = 50, status: Optional[str] = None):
    """List tasks."""
    from app.models.schema import TaskStatus
    
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    tasks = sm.state.list_tasks(limit=limit, status=status_enum)
    return {"tasks": tasks}


@api_router.post("/tasks/{task_id}/upload")
async def upload_images(task_id: str, files: List[UploadFile] = File(...)):
    """Upload images for a task."""
    from pathlib import Path
    from app.utils import utils
    
    task_dir = utils.task_dir(task_id)
    images_dir = task_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded = []
    for i, file in enumerate(files, 1):
        file_path = images_dir / f"{i:03d}.png"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        uploaded.append(str(file_path))
    
    return {
        "task_id": task_id,
        "uploaded": len(uploaded),
        "files": uploaded,
    }


@api_router.get("/templates/scripts")
async def list_script_templates():
    """List available script templates."""
    templates = templating.engine.list_script_templates()
    return {"templates": [t.dict() for t in templates]}


@api_router.get("/templates/prompts")
async def list_prompt_templates():
    """List available prompt templates."""
    templates = templating.engine.list_prompt_templates()
    return {"templates": [t.dict() for t in templates]}


@api_router.get("/templates/styles")
async def list_style_configs():
    """List available style configs."""
    configs = templating.engine.list_style_configs()
    return {"styles": [c.dict() for c in configs]}


@api_router.get("/templates/scripts/{name}")
async def get_script_template(name: str):
    """Get script template content."""
    content = templating.engine.load_script_template(name)
    if not content:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"name": name, "content": content}


@api_router.get("/templates/prompts/{name}")
async def get_prompt_template(name: str):
    """Get prompt template content."""
    content = templating.engine.load_prompt_template(name)
    if not content:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"name": name, "content": content}


@api_router.get("/templates/styles/{name}")
async def get_style_config(name: str):
    """Get style config."""
    style = templating.engine.load_style_config(name)
    if not style:
        raise HTTPException(status_code=404, detail="Style config not found")
    return style.dict()
