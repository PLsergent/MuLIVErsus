import asyncio
from atexit import register
from datetime import datetime, timedelta
import json
from app.mulpyversus.asyncmatches import AsyncMatch
from app.mulpyversus.user import User
from app.mulpyversus.utils import *
import aiohttp
import os


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

    def __init__(
        self,
        user: User,
        mlpyvrs,
        count: int = 1,
        all_pages: bool = False,
        session: aiohttp.ClientSession = None,
        live: bool = True,
    ):
        self.user = user
        self.mlpyvrs = mlpyvrs
        self.rawData = []
        self.matches = []
        self.all_pages = all_pages
        self.count = count
        self.session = session
        self.live = live
        self.expiration = None
        self.last_match = None

    async def init(self):
        if not self.live and await self.check_cache():
            return
        page = 1
        total_pages = 1
        while page <= total_pages:
            result = await self.mlpyvrs.request_data(
                f"matches/all/{self.user.get_account_id()}?count={self.count}&page={page}",
                session=self.session,
            )
            if type(result) is aiohttp.ClientResponse:
                result = await result.json()
            total_pages = result["total_pages"] if self.all_pages else 1
            if self.live:
                self.last_match = result["matches"][0]
                return
            self.rawData.extend(result["matches"])
            page += 1
        await self.write_cache()

    def __repr__(self):
        return str(self.rawData)

    async def load_json_data(self):
        """Load the data from the json file"""
        if os.path.exists(f"./app/cache/{self.user.get_account_id()}.json"):
            with open(f"./app/cache/{self.user.get_account_id()}.json", "r") as f:
                data = json.load(f)
                self.rawData = data["history"]
                self.matches = data["matches"]
                self.expiration = data["expiration"]
                return True

    async def check_cache(self):
        """Check if the user has a cache file"""
        try:
            if await self.load_json_data():
                expiration_date = datetime.strptime(
                    self.expiration, "%Y-%m-%dT%H:%M:%S+00:00"
                )
                if (expiration_date > datetime.now()) and self.rawData and self.matches:
                    return True
            self.rawData = []
            self.matches = []
            self.expiration = None
            return False
        except:
            os.remove(f"./app/cache/{self.user.get_account_id()}.json")

    async def write_cache(self):
        """Write the cache file"""
        data = {
            "expiration": (datetime.now() + timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%S+00:00"
            ),
            "history": self.rawData[1:],
            "matches": self.matches,
        }
        with open(
            f"./app/cache/{self.user.get_account_id()}.json", "w", encoding="utf-8"
        ) as f:
            json.dump(data, f)

    async def get_last_match(self):
        """Returns the last match of this user"""
        if self.last_match:
            last_match_obj = AsyncMatch(self.last_match["id"], self.mlpyvrs)
            await last_match_obj.init()
            return last_match_obj
        else:
            return None

    async def get_matches(self):
        """Returns a list of matches from the user history"""
        if self.matches:
            return self.matches, True
        if self.rawData:
            matches = []
            for match in self.rawData[1:]:
                if match["state"] == "complete":
                    match = AsyncMatch(match["id"], self.mlpyvrs)
                    matches.append(match)
            await asyncio.gather(*[match.init(self.session) for match in matches])
            self.matches = [match.rawData for match in matches]
            await self.write_cache()
            return self.matches, False
        else:
            return [], False
    
    async def get_expiration_date(self):
        """Returns the expiration date of the cache file"""
        return datetime.strptime(self.expiration, "%Y-%m-%dT%H:%M:%S+00:00") if self.expiration else None
