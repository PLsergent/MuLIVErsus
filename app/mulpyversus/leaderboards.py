import json
import string
from app.mulpyversus.mulpyversus import *
from app.mulpyversus.user import *
from app.mulpyversus.utils import *


class UserLeaderboardForGamemode:
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
        self.gamemode = gamemode
        if character_slug is None:
            self.data = json.loads(
                mlpyvrs.request_data(
                    f"leaderboards/{gamemode.value}/score-and-rank/" + str(id)
                ).content
            )
        else:
            self.data = json.loads(
                mlpyvrs.request_data(
                    f"leaderboards/{character_slug}_{gamemode.value}/score-and-rank/"
                    + str(id)
                ).content
            )

    def refresh(self):
        """Used to UserLeaderboard a User object
        Usage Example:
            ::
            leaderbord.refresh_user()
        """
        self.__init__(self.get_account_id(), self)

    def get_account_id(self) -> string:
        return self.data["member"]

    def get_score_in_gamemode(self):
        return self.data["score"] if "score" in self.data else None

    def get_rank_in_gamemode(self):
        return self.data["rank"] if "rank" in self.data else None


class GlobalLeaderboard:
    """Represent a GlobalLeaderboard object
    ::
    Attributes:
    ::
    countLimit : limits the amount of result you get
    """

    def __init__(self, mlpyvrs, gamemode: GamemodeRank, countLimit: int):
        self.rawData = json.loads(
            mlpyvrs.request_data(
                "leaderboards/" + gamemode.value + "/show?count=" + str(countLimit)
            ).content
        )
        self.mlpyvrs = mlpyvrs
        self.countLimit = countLimit

    def get_users_in_leaderboard(self) -> list[User]:
        """Returns a list of users objects from the leaderboard"""
        return [
            User(userLead["member"], self.mlpyvrs)
            for userLead in self.rawData["leaders"]
        ]

    def get_user_in_leaderboard(self, id):
        """Returns the specified user from the leaderboard
        ::
        id : starts at 1, to get first result from leaderboard -> get_user_in_leaderboard(1)
        """
        if id < self.countLimit:
            return User(self.rawData["leaders"][id + 1]["member"], self.mlpyvrs)
        else:
            return None

    def get_user_rank_in_leaderbord(self, id):
        """Returns the specified user RANK from the leaderboard
        ::
        id : starts at 1, to get first result from leaderboard -> get_user_in_leaderboard(1)
        """
        if id < self.countLimit:
            return self.rawData["leaders"][id + 1]["rank"]
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
