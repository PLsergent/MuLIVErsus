import asyncio
import traceback
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
from app.mulpyversus.utils import (
    GamemodeMatches,
    GamemodeRank,
    GamemodeRating,
    RatingKeys,
    get_character_from_slug,
)
from app.mulpyversus.mulpyversus import MulpyVersus
from app.mulpyversus.asyncmulpyversus import AsyncMulpyVersus
import os
from starlette.middleware.sessions import SessionMiddleware


with open("./app/.config.yml", "r") as stream:
    data = yaml.safe_load(stream)

STEAM_TOKEN = data["steam_token"]
mlpyvrs = MulpyVersus(STEAM_TOKEN)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=f"{os.urandom(24).hex()}")

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "Home"}
    )


@app.post("/")
def login(username: str = Form()):
    return RedirectResponse(f"/{username}", status_code=303)


async def get_user_info_for_gamemode(
    mlpyvrs, id, gmrating: GamemodeRating, gmrank: GamemodeRank, match=None, user=None
):
    info = {}

    if user is None:
        user = mlpyvrs.get_user_by_id(id)
    else:
        user = user
    info["id"] = user.get_account_id()
    for network in user.get_user_networks():
        if network.get_network_name() == "wb_network":
            info["username"] = network.get_network_user_username()
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
    info["rating"] = int(user.get_character_rating(char, RatingKeys.Mean, gmrating))
    info["rank"] = -1
    rank = (
        mlpyvrs.get_user_leaderboard(
            user.get_account_id(), gmrank, character_slug=character_slug
        ).get_rank_in_gamemode()
        if match is not None
        else mlpyvrs.get_user_leaderboard(
            user.get_account_id(), gmrank
        ).get_rank_in_gamemode()
    )
    if rank is not None:
        info["rank"] = "{:,}".format(rank)

    info["rating_updates"] = 0
    info["score"] = ""
    if match is not None and match.get_state() != "open":
        info["rating_updates"] = (
            match.get_rating_update(info["id"])
            if match.get_rating_update(info["id"]) is not None
            else 0
        )
        info["score"] = match.get_player_data_by_id(info["id"]).get_score()
    return info


async def get_char_infos(character_slug: str, user, wins):
    character = get_character_from_slug(character_slug)
    rankOvO = mlpyvrs.get_user_leaderboard(
        user.get_account_id(),
        GamemodeRank.OneVsOne,
        character_slug=character_slug,
    ).get_rank_in_gamemode()
    rankTvT = mlpyvrs.get_user_leaderboard(
        user.get_account_id(),
        GamemodeRank.TwoVsTwo,
        character_slug=character_slug,
    ).get_rank_in_gamemode()
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


@app.get("/{id}")
async def profile(request: Request, id: str):
    try:
        user_search_results = mlpyvrs.get_user_by_username(id)
        if user_search_results is not None:
            user = user_search_results.get_most_relevant_user()
        else :
            user = mlpyvrs.get_user_by_id(id)

        if (
            "code" in user.profileData and user.get_code() == 404
        ) or "stat_trackers" not in user.profileData["server_data"]:
            return templates.TemplateResponse(
                "404.html",
                {
                    "request": request,
                    "title": "No data found",
                    "message": "No data found for this user.",
                },
            )

        total_win = user.get_match_won_count(
            GamemodeMatches.OneVsOne
        ) + user.get_match_won_count(GamemodeMatches.TwoVsTwo)
        total_loss = user.get_match_lost_count(
            GamemodeMatches.OneVsOne
        ) + user.get_match_lost_count(GamemodeMatches.TwoVsTwo)
        total_win_percentage = round(user.get_global_win_percentage(), 2)

        # Top characters
        top_characters_slug = user.get_top_character_wins(9)

        top_characters = await asyncio.gather(
            *[
                get_char_infos(character_slug, user, wins)
                for character_slug, wins in top_characters_slug.items()
            ]
        )

        gamemode_results = await asyncio.gather(
            *[
                get_user_info_for_gamemode(
                    mlpyvrs,
                    user.get_account_id(),
                    GamemodeRating.OneVsOne,
                    GamemodeRank.OneVsOne,
                    user=user,
                ),
                get_user_info_for_gamemode(
                    mlpyvrs,
                    user.get_account_id(),
                    GamemodeRating.TwoVsTwo,
                    GamemodeRank.TwoVsTwo,
                    user=user,
                ),
            ]
        )

        OneVsOne_infos = gamemode_results[0]
        TwoVsTwo_infos = gamemode_results[1]

        username = OneVsOne_infos["username"]
    except:
        traceback.print_exc()
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "title": "Error",
                "message": "Error while fetching data.",
            },
        )

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "title": "Profile",
            "username": username,
            "user": user,
            "total_win": total_win,
            "total_loss": total_loss,
            "total_win_percentage": total_win_percentage,
            "top_characters": top_characters,
            "OneVsOne_infos": OneVsOne_infos,
            "TwoVsTwo_infos": TwoVsTwo_infos,
        },
    )


@app.get("/{id}/live")
async def live(request: Request, id: str):
    try:
        user = mlpyvrs.get_user_by_id(id)
        if "code" in user.profileData and user.get_code() == 404:  
            user_search_results = mlpyvrs.get_user_by_username(id)
            if user_search_results is not None:
                user = user_search_results.get_most_relevant_user()
            else :
                return templates.TemplateResponse(
                    "404.html",
                    {
                        "request": request,
                        "title": "No data found",
                        "message": "No data found for this user.",
                    },
                )
        for network in user.get_user_networks():
            if network.get_network_name() == "wb_network":
                username = network.get_network_user_username()

        user_match_history = mlpyvrs.get_user_match_history(user)
        last_match = user_match_history.get_last_match()

        if last_match is None:
            return templates.TemplateResponse(
                "404.html",
                {
                    "request": request,
                    "title": "No data found",
                    "message": "No match found for this user.",
                },
            )

        state = last_match.get_state()
        if state == "open":
            if len(last_match.rawData["players"]["current"]) == 1:
                match_type = "1v1"
                title = f"Waiting for a game to start..."
            else:
                match_type = (
                    "1v1"
                    if len(last_match.rawData["players"]["current"]) == 2
                    else "2v2"
                )
                title = f"Live - {match_type}"
        else:
            match_type = (
                "1v1" if last_match.get_player_ammount_in_match() == 2 else "2v2"
            )
            title = f"Finished - {match_type}"

        players = []
        gmrating = (
            GamemodeRating.OneVsOne if match_type == "1v1" else GamemodeRating.TwoVsTwo
        )
        gmrank = GamemodeRank.OneVsOne if match_type == "1v1" else GamemodeRank.TwoVsTwo

        jobs = []
        if title.startswith("Live"):
            for id in last_match.rawData["players"]["current"]:
                jobs.append(get_user_info_for_gamemode(mlpyvrs, id, gmrating, gmrank))
        elif title.startswith("Finished"):
            for id in last_match.rawData["win"] + last_match.rawData["loss"]:
                jobs.append(
                    get_user_info_for_gamemode(
                        mlpyvrs, id, gmrating, gmrank, match=last_match
                    )
                )
        players = await asyncio.gather(*jobs)

    except:
        traceback.print_exc()
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "title": "Error",
                "message": "Error while fetching data.",
            },
        )

    return templates.TemplateResponse(
        "live.html",
        {"request": request, "title": title, "username": username, "user": user, "players": players},
    )
