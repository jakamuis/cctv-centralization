from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.site import Site


class SiteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, site_id: str) -> Optional[Site]:
        result = await self.session.execute(select(Site).where(Site.id == site_id))
        return result.scalars().first()

    async def list(self, offset: int = 0, limit: int = 100) -> List[Site]:
        result = await self.session.execute(select(Site).offset(offset).limit(limit))
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.session.execute(select(Site))
        return len(result.scalars().all())

    async def create(self, site: Site) -> Site:
        self.session.add(site)
        await self.session.commit()
        await self.session.refresh(site)
        return site

    async def update(self, site: Site) -> Site:
        self.session.add(site)
        await self.session.commit()
        await self.session.refresh(site)
        return site

    async def delete(self, site: Site) -> None:
        await self.session.delete(site)
        await self.session.commit()