from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.site import Site
from app.schemas.site import SiteCreate, SiteUpdate
from app.repositories.site import SiteRepository


class SiteService:
    def __init__(self, session: AsyncSession):
        self.repo = SiteRepository(session)

    async def get_site(self, site_id: str) -> Optional[Site]:
        return await self.repo.get(site_id)

    async def list_sites(self, offset: int = 0, limit: int = 100) -> List[Site]:
        return await self.repo.list(offset=offset, limit=limit)

    async def count_sites(self) -> int:
        return await self.repo.count()

    async def create_site(self, site_in: SiteCreate) -> Site:
        site = Site(**site_in.model_dump())
        return await self.repo.create(site)

    async def update_site(self, site: Site, site_in: SiteUpdate) -> Site:
        for field, value in site_in.model_dump(exclude_unset=True).items():
            setattr(site, field, value)
        return await self.repo.update(site)

    async def delete_site(self, site: Site) -> None:
        await self.repo.delete(site)