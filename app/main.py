from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
from mulpyversus.utils import GamemodeMatches, GamemodeRank, GamemodeRating, Characters, RatingKeys, get_character_from_slug

from mulpyversus.mulpyversus import MulpyVersus

with open(".config.yml", 'r') as stream:
    data = yaml.safe_load(stream)

STEAM_TOKEN = data["steam_token"]

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Home"})

@app.post("/")
def login(username: str = Form()):
    return RedirectResponse(f"/{username}", status_code=303)

def get_user_info_for_gamemode(mlpyvrs, user, gmrating : GamemodeRating, gmrank : GamemodeRank):
    info = {}
    info["id"] = user.get_account_id()
    for network in user.get_user_networks():
        if network.get_network_name() == "wb_network":
            info["username"] = network.get_network_user_username()
    info["total_win"] = user.get_match_won_count(GamemodeMatches.OneVsOne)+user.get_match_won_count(GamemodeMatches.TwoVsTwo)
    info["total_loss"] = user.get_match_lost_count(GamemodeMatches.OneVsOne)+user.get_match_lost_count(GamemodeMatches.TwoVsTwo)
    info["total_win_percentage"] = round(user.get_global_win_percentage(), 2)
    info["total_ringouts"] = user.get_total_ringouts()
    OneVsOne_slug_topranked = user.get_top_ranked_character_in_gamemode(gmrating)
    char = get_character_from_slug(OneVsOne_slug_topranked)
    info["top_ranked_win"] = user.get_wins_with_character(char)
    info["char_top_ranked"] = char.value["name"] 
    info["top_rating"] = round(user.get_character_rating(char, RatingKeys.Mean, gmrating), 0)
    info["top_rank"] = -1
    if mlpyvrs.get_user_leaderboard(user.get_account_id()).get_rank_in_gamemode(gmrank) is not None:
        info["top_rank"] = "{:,}".format(mlpyvrs.get_user_leaderboard(user.get_account_id()).get_rank_in_gamemode(gmrank))
    return info

@app.get("/{id}")
def profile(request: Request, id: str):
    mlpyvrs = MulpyVersus(STEAM_TOKEN)
    try:
        user = mlpyvrs.get_user_by_username(id)
    except:
        user = mlpyvrs.get_user_by_id(id)

    if "stat_trackers" not in user.profileData['server_data']:
        return templates.TemplateResponse("404.html", {"request": request, "title": "No data found", "message": "No data found for this user."})

    total_win = user.get_match_won_count(GamemodeMatches.OneVsOne)+user.get_match_won_count(GamemodeMatches.TwoVsTwo)
    total_loss = user.get_match_lost_count(GamemodeMatches.OneVsOne)+user.get_match_lost_count(GamemodeMatches.TwoVsTwo)
    total_win_percentage = round(user.get_global_win_percentage(), 2)

    # Top characters
    top_characters_slug = user.get_top_character_wins()
    top_characters = {}
    for character_slug, wins in top_characters_slug.items():
        character = get_character_from_slug(character_slug)
        top_characters[character.value["name"]] = {
            "wins": wins,
            "OvO_MMR": round(user.get_character_rating(character, RatingKeys.Mean, GamemodeRating.OneVsOne), 0),
            "TvT_MMR": round(user.get_character_rating(character, RatingKeys.Mean, GamemodeRating.TwoVsTwo), 0)
        }

    # 1v1
    OneVsOne_infos = get_user_info_for_gamemode(mlpyvrs, user, GamemodeRating.OneVsOne, GamemodeRank.OneVsOne)

    # 2v2
    TwoVsTwo_infos = get_user_info_for_gamemode(mlpyvrs, user, GamemodeRating.TwoVsTwo, GamemodeRank.TwoVsTwo)

    username = OneVsOne_infos["username"]
        
    return templates.TemplateResponse("profile.html",
        {"request": request, "title": "Profile", "username": username, "user": user,
        "total_win": total_win, "total_loss": total_loss, "total_win_percentage": total_win_percentage,
        "top_characters": top_characters,
        "OneVsOne_infos": OneVsOne_infos, "TwoVsTwo_infos": TwoVsTwo_infos})
    
@app.get("/{id}/live")
def live(request: Request, id: str):
    mlpyvrs = MulpyVersus(STEAM_TOKEN)
    try:
        user = mlpyvrs.get_user_by_username(id)
    except:
        user = mlpyvrs.get_user_by_id(id)
    
    for network in user.get_user_networks():
        if network.get_network_name() == "wb_network":
            username = network.get_network_user_username()
    user_match_history = mlpyvrs.get_user_match_history(user)
    last_match = user_match_history.get_last_match()

    if last_match is None:
        return templates.TemplateResponse("404.html", {"request": request, "title": "No data found", "message": "No match found for this user."})

    state = last_match.get_state()
    if state == "open":
        if len(last_match.rawData["players"]["current"]) == 1:
            match_type = "1v1"
            title = f"Waiting for a game to start..."
        else:
            match_type = "1v1" if len(last_match.rawData["players"]["current"]) == 2 else "2v2"
            title = f"Live - {match_type}"
    else:
        match_type = "1v1" if last_match.get_player_ammount_in_match() == 2 else "2v2"
        title = f"Finished - {match_type}"
    
    players = []
    gmrating = GamemodeRating.OneVsOne if match_type == "1v1" else GamemodeRating.TwoVsTwo
    gmrank = GamemodeRank.OneVsOne if match_type == "1v1" else GamemodeRank.TwoVsTwo
    if title.startswith("Live"):
        for id in last_match.rawData["players"]["current"]:
            players.append(get_user_info_for_gamemode(mlpyvrs, mlpyvrs.get_user_by_id(id), gmrating, gmrank))
    elif title.startswith("Finished"):
        for id in last_match.rawData["win"] + last_match.rawData["loss"]:
            players.append(get_user_info_for_gamemode(mlpyvrs, mlpyvrs.get_user_by_id(id), gmrating, gmrank))
    
    return templates.TemplateResponse("live.html", {"request": request, "title": title, "username": username, "players": players})