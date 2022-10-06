import asyncio
from app.mulpyversus.asyncmatches import AsyncMatch
from app.mulpyversus.user import User
from app.mulpyversus.utils import *
import aiohttp

class AsyncUserMatchHistory:
    """Represent the match history of a user
    ::
    Args:
        data: result of a matches request
        ::
    Usage Example:
        user = mlp.get_user_by_id("XXXXXXXX")
        user_match_history = UserMatchHistory(user, mlpyvrs)
    """
    def __init__(self, user : User, mlpyvrs, count : int = 1, all_pages : bool = False):
        self.user = user
        self.mlpyvrs = mlpyvrs
        self.rawData = []
        self.all_pages = all_pages
        self.count = count
    
    async def init(self):
        page = 1
        total_pages = 1
        while page <= total_pages:
            result = await self.mlpyvrs.request_data(f"matches/all/{self.user.get_account_id()}?count={self.count}&page={page}")
            if type(result) is aiohttp.ClientResponse:
                result = await result.json()
            total_pages = result["total_pages"] if self.all_pages else 1
            self.rawData.extend(result["matches"])
            page += 1
    
    def __repr__(self):
        return str(self.rawData)
    
    async def get_last_match(self):
        """Returns the last match of this user"""
        if self.rawData:
            last_match = AsyncMatch(self.rawData[0]["id"], self.mlpyvrs)
            await last_match.init()
            return last_match
        else:
            return None
    
    async def get_matches(self):
        """Returns a list of matches of a specific gamemode"""
        if self.rawData:
            matches = []
            for match in self.rawData[1:]:
                if match["state"] == "complete":
                    match = AsyncMatch(match["id"], self.mlpyvrs)
                    matches.append(match)
            await asyncio.gather(*[match.init() for match in matches])
            return matches
        else:
            return []