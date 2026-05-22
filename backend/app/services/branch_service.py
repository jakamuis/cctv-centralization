from app.models.branch import Branch
from app.repositories.branch import BranchRepository

class BranchService:

    def __init__(self, session):
        self.repo = BranchRepository(session)

    async def get_branch(self, branch_id):
        return await self.repo.get(branch_id)

    async def list_branches(self, skip: int = 0, limit: int = 100):
        result = await self.repo.list(skip=skip, limit=limit)
        return result

    async def count_branches(self):
        result = await self.repo.list(skip=0, limit=100000)
        return result["total"]