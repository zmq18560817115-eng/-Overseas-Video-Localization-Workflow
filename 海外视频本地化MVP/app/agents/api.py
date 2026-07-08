"""Agent 状态 API。

main.py 只需在文件末尾（startup 事件附近）追加两行，不动现有路由：

    from .agents.api import router as agents_router
    app.include_router(agents_router)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from .orchestrator import evaluate_material

router = APIRouter()


@router.get("/api/materials/{link_id}/agent-state")
async def material_agent_state(link_id: int) -> dict:
    decision = await run_in_threadpool(evaluate_material, link_id)
    if decision.current_stage == "material_missing":
        raise HTTPException(status_code=404, detail=decision.blockers[0])
    return decision.to_dict()
