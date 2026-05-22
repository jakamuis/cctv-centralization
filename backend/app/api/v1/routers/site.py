from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.site import Site as SiteModel
from app.schemas.site import (
    Site,
    SiteCreate,
    SiteUpdate,
    SiteList,
)

router = APIRouter(
    prefix="/sites",
    tags=["Sites"],
)


@router.get(
    "/",
    response_model=SiteList,
    summary="List sites with pagination",
)
async def list_sites(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):

    from sqlalchemy import select

    result = await db.execute(
        select(SiteModel).offset(skip).limit(limit)
    )

    items = result.scalars().all()

    return {
        "items": items,
        "total": len(items),
    }


@router.post(
    "/",
    response_model=Site,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new site",
)
async def create_site(
    payload: SiteCreate,
    db: AsyncSession = Depends(get_db),
):

    site = SiteModel(**payload.model_dump())

    db.add(site)

    await db.commit()

    await db.refresh(site)

    return site


@router.get(
    "/{site_id}",
    response_model=Site,
    summary="Get site details by ID",
)
async def get_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    from sqlalchemy import select

    result = await db.execute(
        select(SiteModel).where(SiteModel.id == site_id)
    )

    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=404,
            detail="Site not found",
        )

    return site


@router.put(
    "/{site_id}",
    response_model=Site,
    summary="Update site details",
)
async def update_site(
    site_id: UUID,
    payload: SiteUpdate,
    db: AsyncSession = Depends(get_db),
):

    from sqlalchemy import select

    result = await db.execute(
        select(SiteModel).where(SiteModel.id == site_id)
    )

    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=404,
            detail="Site not found",
        )

    for key, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(site, key, value)

    await db.commit()

    await db.refresh(site)

    return site


@router.delete(
    "/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a site",
)
async def delete_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    from sqlalchemy import select

    result = await db.execute(
        select(SiteModel).where(SiteModel.id == site_id)
    )

    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(
            status_code=404,
            detail="Site not found",
        )

    await db.delete(site)

    await db.commit()