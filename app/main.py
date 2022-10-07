import asyncio
import traceback
from typing import List, Union
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
from app.mulpyversus.utils import (
    GamemodeRank,
    GamemodeRating,
    slug_to_display,
)
from app.mulpyversus.asyncmulpyversus import AsyncMulpyVersus
import os
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from app.utils.utils_process import *


app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=f"{os.urandom(24).hex()}")

templates = Jinja2Templates(directory="app/templates")

with open("./app/.config.yml", "r") as stream:
    data = yaml.safe_load(stream)
STEAM_TOKEN_MAIN = data["steam_token_main"]
mlpyvrs = AsyncMulpyVersus(STEAM_TOKEN_MAIN)

if "steam_token_stats" in data:
    STEAM_TOKEN_STATS = data["steam_token_stats"]
    mlpyvrs_stats = AsyncMulpyVersus(STEAM_TOKEN_STATS)

if "steam_token_live" in data:
    STEAM_TOKEN_LIVE = data["steam_token_live"]
    mlpyvrs_live = AsyncMulpyVersus(STEAM_TOKEN_LIVE)


@app.on_event("startup")
async def startup_event():
    await mlpyvrs.init()
    if "steam_token_stats" in data:
        await mlpyvrs_stats.init()
    if "steam_token_live" in data:
        await mlpyvrs_live.init()


@app.on_event("shutdown")
async def shutdown_event():
    await mlpyvrs.close_session()
    if "steam_token_stats" in data:
        await mlpyvrs_stats.close_session()
    if "steam_token_live" in data:
        await mlpyvrs_live.close_session()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "Home"}
    )


@app.post("/")
def login(username: str = Form()):
    return RedirectResponse(f"/{username}", status_code=303)


# /id?slugs=slug1&slugs=slug2
@app.get("/{id}/winrate")
async def winrate_against_char(request: Request, id: str, slugs: Union[List[str], None] = Query(default=None)):
    try:
        user = await mlpyvrs.get_user_by_id(id)
        if "code" in user.profileData and user.get_code() == 404:
            user_search_results = await mlpyvrs.get_user_by_username(id)
            if user_search_results is not None:
                user = await user_search_results.get_most_relevant_user()
            else:
                return templates.TemplateResponse("winrate_live.html", {"request": request, "error": True})
        
        if "steam_token_live" in data:
            match_history = await mlpyvrs_live.get_user_match_history(user, count=200, all_pages=False)
        else:
            match_history = await mlpyvrs.get_user_match_history(user, count=200, all_pages=False)
        history_for_gamemode = await match_history.get_matches()
        winrate, matches_analyzed = await get_winrate_against_char(history_for_gamemode, user.get_account_id())
        winrates = {}
        for slug in slugs:
            if slug in winrate:
                winrates[slug_to_display(slug)] = winrate[slug]
        return templates.TemplateResponse(
            "winrate_live.html",
            {
                "request": request,
                "winrates": winrates,
                "matches_analyzed": matches_analyzed
            }
        )
    except:
        traceback.print_exc()
        return templates.TemplateResponse("winrate_live.html", {"request": request, "error": True})


@app.get("/{id}")
async def profile(request: Request, id: str):
    try:
        user_search_results = await mlpyvrs.get_user_by_username(id)
        if user_search_results is not None:
            user = await user_search_results.get_most_relevant_user()

        if user_search_results is None or user is None:
            user = await mlpyvrs.get_user_by_id(id)

        if (
            user is None or "code" in user.profileData and user.get_code() == 404
        ) or "stat_trackers" not in user.profileData["server_data"]:
            return templates.TemplateResponse(
                "404.html",
                {
                    "request": request,
                    "title": "No data found",
                    "message": "No data found for this user.",
                },
            )

        # Top characters
        top_characters_slug = user.get_top_character_wins(9)

        top_characters = await asyncio.gather(
            *[
                get_char_infos(character_slug, user, wins, mlpyvrs)
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
        total_win = OneVsOne_infos["total_win"]
        total_loss = OneVsOne_infos["total_loss"]
        total_win_percentage = OneVsOne_infos["total_win_percentage"]

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


@app.get("/{id}/advanced")
async def advanced_profile(request: Request, id: str):
    try:
        user_search_results = await mlpyvrs.get_user_by_username(id)
        if user_search_results is not None:
            user = await user_search_results.get_most_relevant_user()

        if user_search_results is None or user is None:
            user = await mlpyvrs.get_user_by_id(id)

        if (
            user is None or "code" in user.profileData and user.get_code() == 404
        ) or "stat_trackers" not in user.profileData["server_data"]:
            return templates.TemplateResponse("advanced_stats.html", {"request": request, "error": True})
        
        if "steam_token_stats" in data:
            match_history = await mlpyvrs_stats.get_user_match_history(user, count=30, all_pages=False)
        else:
            match_history = await mlpyvrs.get_user_match_history(user, count=30, all_pages=False)
        history_for_gamemode = await match_history.get_matches()
        adv_stats, matches_analyzed = await get_matchup_stats(history_for_gamemode, user.get_account_id())
        advanced_stats = {}
        for char, stats in adv_stats.items():
            advanced_stats[slug_to_display(char)] = stats
        return templates.TemplateResponse(
            "advanced_profile.html",
            {
                "request": request,
                "advanced_stats": advanced_stats,
                "matches_analyzed": matches_analyzed
            }
        )
    except:
        traceback.print_exc()
        return templates.TemplateResponse("advanced_profile.html", {"request": request, "error": True})


@app.get("/{id}/live")
async def live(request: Request, id: str):
    try:
        user = await mlpyvrs.get_user_by_id(id)
        if "code" in user.profileData and user.get_code() == 404:
            user_search_results = await mlpyvrs.get_user_by_username(id)
            if user_search_results is not None:
                user = await user_search_results.get_most_relevant_user()
            else:
                return templates.TemplateResponse(
                    "404.html",
                    {
                        "request": request,
                        "title": "No data found",
                        "message": "No data found for this user.",
                    },
                )

        user_match_history = await mlpyvrs.get_user_match_history(user)
        last_match = await user_match_history.get_last_match()

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
        time = last_match.get_creation_time()
        if title.startswith("Live"):
            for id in last_match.rawData["players"]["current"]:
                if id == user.get_account_id():
                    jobs.append(
                        get_user_info_for_gamemode(
                            mlpyvrs, id, gmrating, gmrank, user=user
                        )
                    )
                else:
                    jobs.append(
                        get_user_info_for_gamemode(mlpyvrs, id, gmrating, gmrank)
                    )
        elif title.startswith("Finished"):
            time = last_match.get_completion_time()
            for id in last_match.rawData["win"] + last_match.rawData["loss"]:
                if id == user.get_account_id():
                    jobs.append(
                        get_user_info_for_gamemode(
                            mlpyvrs, id, gmrating, gmrank, match=last_match, user=user
                        )
                    )
                else:
                    jobs.append(
                        get_user_info_for_gamemode(
                            mlpyvrs, id, gmrating, gmrank, match=last_match
                        )
                    )
        players = await asyncio.gather(*jobs)
        slugs_url_query = "?slugs=" + "&slugs=".join([player["char_slug"] for player in players if player["id"] != user.get_account_id()])
        timedate = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S+00:00")

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
        {
            "request": request,
            "title": title,
            "user": user,
            "time": timedate,
            "players": players,
            "slugs_url_query": slugs_url_query
        },
    )
