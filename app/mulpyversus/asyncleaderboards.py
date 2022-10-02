import string
from app.mulpyversus.asyncuser import AsyncUser
from app.mulpyversus.mulpyversus import *
from app.mulpyversus.user import *
from app.mulpyversus.utils import *


class AsyncUserLeaderboardForGamemode:
    """Represent a UserLeaderboard object
    ::
        ::
    Usage Example:
            a
    Attributes:
    """

    def __init__(
        self, mlpyvrs, id: string, gamemode: GamemodeRank, character_slug: string = None
    ):
        self.id = id
        self.mlpyvrs = mlpyvrs
        self.gamemode = gamemode
        self.character_slug = character_slug

    async def init(self):
        if self.character_slug is None:
            self.data = await self.mlpyvrs.request_data(
                f"leaderboards/{self.gamemode.value}/score-and-rank/{str(self.id)}"
            )
        else:
            self.data = await self.mlpyvrs.request_data(
                f"leaderboards/{self.character_slug}_{self.gamemode.value}/score-and-rank/{str(self.id)}"
            )

    async def refresh(self):
        """Used to refresh a AsyncUserLeaderboard object
        Usage Example:
            ::
            leaderbord.refresh_user()
        """
        await self.init(self.get_account_id(), self)

    def get_account_id(self) -> string:
        return self.data["member"]

    def get_score_in_gamemode(self):
        return self.data["score"] if "score" in self.data else None

    def get_rank_in_gamemode(self):
        return self.data["rank"] if "rank" in self.data else None


class AsyncGlobalLeaderboard:
    """Represent a GlobalLeaderboard object
    ::
    Attributes:
    ::
    countLimit : limits the amount of result you get
    """

    def __init__(self, mlpyvrs, gamemode: GamemodeRank, countLimit: int):
        self.mlpyvrs = mlpyvrs
        self.countLimit = countLimit
        self.gamemode = gamemode

    async def init(self):
        self.rawData = await self.mlpyvrs.request_data(
            "leaderboards/"
            + self.gamemode.value
            + "/show?count="
            + str(self.countLimit)
        )

    async def get_users_in_leaderboard(self) -> list[User]:
        """IS ASYNC
        ::
        Returns a list of AsyncUser objects from the leaderboard
        """
        users = []
        for userLead in self.rawData["leaders"]:
            newUser = AsyncUser(userLead["member"], self.mlpyvrs)
            await newUser.init()
            users.append(newUser)
        return users

    async def get_user_in_leaderboard(self, id):
        """IS ASYNC
        ::
        Returns the specified user from the leaderboard
        ::
        id : starts at 1, to get first result from leaderboard -> get_user_in_leaderboard(1)
        """
        if id < self.countLimit:
            newUser = AsyncUser(self.rawData["leaders"][id + 1]["member"], self.mlpyvrs)
            await newUser.init()
            return newUser
        else:
            return None

    async def get_user_rank_in_leaderbord(self, id):
        """IS ASYNC
        ::
        Returns the specified user RANK from the leaderboard
        ::
        id : starts at 1, to get first result from leaderboard -> get_user_in_leaderboard(1)
        """
        if id < self.countLimit:
            newUser = AsyncUser(self.rawData["leaders"][id + 1]["rank"], self.mlpyvrs)
            await newUser.init()
            return newUser
        else:
            return None

    def get_user_score_in_leaderbord(self, id):
        """Returns the specified user RANK from the leaderboard
        ::
        id : starts at 1, to get first result from leaderboard -> get_user_in_leaderboard(1)
        """
        if id < self.countLimit:
            return self.rawData["leaders"][id + 1]["score"]
        else:
            return None

    def get_account_id_in_leaderbord(self, id):
        if id < self.countLimit:
            return self.rawData["leaders"][id + 1]["member"]
        else:
            return None

    def get_user_networks_in_leaderbord(self, id) -> list[UserNetwork]:
        return [
            UserNetwork(
                self.rawData["leaders"]["identity"]["alternate"][name],
                name,
                self.get_account_id_in_leaderbord(),
            )
            for name in self.rawData["leaders"]["identity"]["alternate"]
        ]

    def has_network_in_leaderbord(self, network: Networks):
        """Returns Network objects for specified network
        ::
        Returns False if network not found in the user's network list
        """
        return (
            UserNetwork(
                self.rawData["leaders"]["identity"]["alternate"][network.value],
                network.value,
                self.get_account_id_in_leaderbord(),
            )
            if network.value in self.rawData["leaders"]["identity"]["alternate"]
            else False
        )

    def get_match_lost_count_in_leaderbord(self, gm: GamemodeMatches):
        """Return amount of games lost in specified GamemodeMatches
        ::
        Args:
            To use this, use GamemodeMatches.NAMEOFGAMEMODE
        ::
        Usage Example:
            >>> .get_match_lost_count(GamemodeMatches.NAMEOGAMEMODE)
        """
        return (
            self.rawData["leaders"]["profile"]["matches"][gm.value]["loss"]
            if gm.value in self.rawData["leaders"]["profile"]["matches"]
            else 0
        )

    def get_match_won_count_in_leaderbord(self, gm: GamemodeMatches):
        """Return amount of games won in specified GamemodeMatches
        ::
        Args:
            To use this, use GamemodeMatches.NAMEOFGAMEMODE
        ::
        Usage Example:
            >>> .get_match_won_count(GamemodeMatches.NAMEOGAMEMODE)
        """
        return (
            self.rawData["leaders"]["profile"]["matches"][gm.value]["win"]
            if gm.value in self.rawData["leaders"]["profile"]["matches"]
            else 0
        )

    def get_win_streak_count_in_leaderbord(self, gm: GamemodeMatches):
        """Return current winstreak in specified GamemodeMatches
        ::
        Args:
            To use this, use GamemodeMatches.NAMEOFGAMEMODE
        ::
        Usage Example:
            >>> .get_win_streak_count(GamemodeMatches.NAMEOGAMEMODE)
        """
        return (
            self.rawData["leaders"]["profile"]["matches"][gm.value]["win_streak"]
            if gm.value in self.rawData["leaders"]["profile"]["matches"]
            else 0
        )

    def get_longest_win_streak_in_leaderbord(self, gm: GamemodeMatches):
        """Return return longest winstreak specified GamemodeMatches
        ::
        Args:
            To use this, use GamemodeMatches.NAMEOFGAMEMODE
        ::
        Usage Example:
            >>> .get_win_streak_count(GamemodeMatches.NAMEOGAMEMODE)
        """
        return (
            self.rawData["leaders"]["profile"]["matches"][gm.value][
                "longest_win_streak"
            ]
            if gm.value in self.rawData["leaders"]["profile"]["matches"]
            else 0
        )
