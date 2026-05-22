from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.schemas.branch import Branch, BranchList
from app.services.branch_service import BranchService
from app.api.v1.dependencies import get_db

router = APIRouter()

@router.get("/branches", response_model=BranchList)
async def list_branches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    service = BranchService(db)
    result = await service.list_branches(skip=skip, limit=limit)
    return BranchList(total=result["total"], items=result["items"])

@router.get("/branches/{branch_id}", response_model=Branch)
async def get_branch(
    branch_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = BranchService(db)
    branch = await service.get_branch(branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch