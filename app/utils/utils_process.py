from app.mulpyversus.utils import (
    GamemodeMatches,
    GamemodeRank,
    GamemodeRating,
    RatingKeys,
    get_character_from_slug,
    slug_to_display,
)


async def get_user_info_for_gamemode(
    mlpyvrs, id, gmrating: GamemodeRating, gmrank: GamemodeRank, match=None, user=None
):
    info = {}
    if user is None:
        user = await mlpyvrs.get_user_by_id(id)
    else:
        user = user
    info["id"] = user.get_account_id()
    info["username"] = user.get_username()

    info["total_win"] = user.get_match_won_count(
        GamemodeMatches.OneVsOne
    ) + user.get_match_won_count(GamemodeMatches.TwoVsTwo)
    info["total_loss"] = user.get_match_lost_count(
        GamemodeMatches.OneVsOne
    ) + user.get_match_lost_count(GamemodeMatches.TwoVsTwo)
    info["total_win_percentage"] = round(user.get_global_win_percentage(), 2)
    info["total_ringouts"] = user.get_total_ringouts()

    character_slug = (
        user.get_top_ranked_character_in_gamemode(gmrating)
        if match is None
        else match.get_player_data_by_id(info["id"]).get_character_slug()
    )
    char = get_character_from_slug(character_slug)
    info["ranked_win"] = user.get_wins_with_character(char)
    info["char"] = char.value["name"]
    info["char_slug"] = character_slug
    info["rating"] = int(user.get_character_rating(char, RatingKeys.Mean, gmrating))

    info["rank"] = -1
    if match is not None:
        leaderboard = await mlpyvrs.get_user_leaderboard(
            user.get_account_id(), gmrank, character_slug=character_slug
        )
    else:
        leaderboard = await mlpyvrs.get_user_leaderboard(user.get_account_id(), gmrank)
    rank = leaderboard.get_rank_in_gamemode() if leaderboard is not None else None
    if rank is not None:
        info["rank"] = "{:,}".format(rank)

    info["top_win_char"] = slug_to_display(
        list(user.get_top_character_wins(1).keys())[0]
    )

    # match info
    info["rating_updates"] = 0
    info["won"] = None
    if match is not None and match.get_state() != "open":
        info["rating_updates"] = (
            match.get_rating_update(info["id"])
            if match.get_rating_update(info["id"]) is not None
            else 0
        )
        info["ringouts"] = match.get_player_data_by_id(info["id"]).get_ringouts_dealt()
        info["dmg_dealt"] = match.get_player_data_by_id(info["id"]).get_damage_dealt()
        info["streak"] = (
            match.get_streak(info["id"])
            if match.get_streak(info["id"]) is not None
            else 0
        )
        info["won"] = True if info["id"] in match.rawData["win"] else False

    return info


async def get_char_infos(character_slug: str, user, wins, mlpyvrs):
    character = get_character_from_slug(character_slug)
    leaderboardOvO = await mlpyvrs.get_user_leaderboard(
        user.get_account_id(),
        GamemodeRank.OneVsOne,
        character_slug=character_slug,
    )
    rankOvO = leaderboardOvO.get_rank_in_gamemode()
    leaderboardTvT = await mlpyvrs.get_user_leaderboard(
        user.get_account_id(),
        GamemodeRank.TwoVsTwo,
        character_slug=character_slug,
    )
    rankTvT = leaderboardTvT.get_rank_in_gamemode()
    if rankOvO is not None:
        rankOvO = "{:,}".format(rankOvO)
    if rankTvT is not None:
        rankTvT = "{:,}".format(rankTvT)

    return {
        "name": character.value["name"],
        "wins": wins,
        "OvO_MMR": int(
            user.get_character_rating(
                character, RatingKeys.Mean, GamemodeRating.OneVsOne
            )
        ),
        "TvT_MMR": int(
            user.get_character_rating(
                character, RatingKeys.Mean, GamemodeRating.TwoVsTwo
            )
        ),
        "OvO_rank": rankOvO,
        "TvT_rank": rankTvT,
    }


async def get_winrate_against_char(usmh, user_id):
    winrate = {}
    analyzed = 0
    for match in usmh:
        match = match.rawData
        if "win" in match: 
            won = True if user_id in match["win"] else False
            opponents = match["loss"] if user_id in match["win"] else match["win"]
            if "server_data" in match and "PlayerData" in match["server_data"]:
                analyzed += 1
                for data in match["server_data"]["PlayerData"]:
                    if data["AccountId"] in opponents:
                        char = data["CharacterSlug"]
                        if char not in winrate:
                            winrate[char] = {"wins": 0, "losses": 0}
                        if won:
                            winrate[char]["wins"] += 1
                        else:
                            winrate[char]["losses"] += 1
    return winrate, analyzed


async def get_matchup_stats(usmh, user_id):
    matchup_stats = {}
    matchup_stats_final = {}
    analyzed = 0
    for match in usmh:
        match = match.rawData
        if "win" in match:
            won = True if user_id in match["win"] else False
            opponents = match["loss"] if user_id in match["win"] else match["win"]
            if "server_data" in match and "PlayerData" in match["server_data"]:
                analyzed += 1
                opponents_stats = []
                slugs_count = {}
                dmg_done = 0
                ringouts = 0
                deaths = 0
                for data in match["server_data"]["PlayerData"]:
                    if data["AccountId"] not in opponents:
                        dmg_done += data["DamageDone"]
                        ringouts += data["Ringouts"]
                        deaths += data["Deaths"]
                    elif data["AccountId"] in opponents:
                        char = data["CharacterSlug"]
                        if char not in slugs_count:
                            slugs_count[char] = 1
                        else:
                            slugs_count[char] += 1
                        if char not in matchup_stats:
                            matchup_stats[char] = {"tot_dmg": 0, "tot_dmg_killed": 0}
                        opponent = {"slug": char, "dmg": data["DamageDone"], "ringouts": data["Ringouts"]}
                        opponents_stats.append(opponent)
                        if char not in matchup_stats_final:
                            matchup_stats_final[char] = {"wins": 0, "losses": 0, "avg_dmg": 0, "avg_dmg_killed": 0, "stock_diff": 0}
                        if won and slugs_count[char] == 1:
                            matchup_stats_final[char]["wins"] += 1
                        elif slugs_count[char] == 1:
                            matchup_stats_final[char]["losses"] += 1
                opponents_dmg = sum([int(op["dmg"]) for op in opponents_stats])
                opponents_ringouts = sum([int(op["ringouts"]) for op in opponents_stats])
                for op in opponents_stats:
                    if slugs_count[op["slug"]] == 1:
                        matchup_stats[op["slug"]]["tot_dmg"] += int(dmg_done / ringouts) if ringouts > 0 else 0
                        matchup_stats[op["slug"]]["tot_dmg_killed"] += int(opponents_dmg / deaths) if deaths != 0 else 0
                        matchup_stats_final[op["slug"]]["stock_diff"] += int(ringouts - opponents_ringouts)
                    else:
                        slugs_count[op["slug"]] -= 1
    for char, matchup in matchup_stats.items():
        total = matchup_stats_final[char]["wins"] + matchup_stats_final[char]["losses"]
        matchup_stats_final[char]["avg_dmg"] = round(matchup["tot_dmg"] / total, 2) if total != 0 else 0
        matchup_stats_final[char]["avg_dmg_killed"] = round(matchup["tot_dmg_killed"] / total, 2) if total != 0 else 0
    return matchup_stats_final, analyzed