import json
from app.mulpyversus.user import User
from app.mulpyversus.matches import Match
from app.mulpyversus.utils import *


class UserMatchHistory:
    """Represent the match history of a user
    ::
    Args:
        data: result of a matches request
        ::
    Usage Example:
        user = mlp.get_user_by_id("XXXXXXXX")
        user_match_history = UserMatchHistory(user, mlpyvrs)
    """
    def __init__(self, user : User, mlpyvrs, all_pages : bool = False):
        self.user = user
        self.mlpyvrs = mlpyvrs
        self.rawData = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            result = json.loads(mlpyvrs.request_data(f"matches/all/{user.get_account_id()}?page={page}").content)
            total_pages = result["total_pages"] if all_pages else 1
            self.rawData.extend(result["matches"])
            page += 1
    
    def __repr__(self):
        return str(self.rawData)
    
    def get_last_match(self):
        """Returns the last match of this user"""
        if self.rawData:
            return Match(self.rawData[0]["id"], self.mlpyvrs)
        else:
            return None