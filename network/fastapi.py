from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from server.match import Match
from server.deck import Deck
from tests.utils_for_test import get_random_state, set_16_omni, make_respond
from agents.nothing_agent import NothingAgent
from agents.interaction_agent import InteractionAgent


app = FastAPI()


# Add the CORSMiddleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:4000', 'https://localhost:4000', 
        'http://127.0.0.1:4000', 'https://127.0.0.1:4000',
    ],
    # allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def get_new_match(seed: Any = None, rich: bool = False):
    deck = Deck.from_str(
        '''
        charactor:Fischl
        charactor:Mona
        charactor:Nahida
        # Gambler's Earrings*2
        # Wine-Stained Tricorne*2
        # Vanarana
        # Timmie*2
        # Rana*2
        # Covenant of Rock
        # Wind and Freedom
        # The Bestest Travel Companion!*2
        # Changing Shifts*2
        # Toss-Up
        # Strategize*2
        # I Haven't Lost Yet!*2
        # Leave It to Me!
        # Clax's Arts*2
        # Adeptus' Temptation*2
        # Lotus Flower Crisp*2
        # Mondstadt Hash Brown*2
        Mondstadt Hash Brown*30
        '''
    )
    # use old version cards
    # old = {'name': 'I Haven\'t Lost Yet!', 'version': '3.3'}
    # deck_dict = deck.dict()
    # deck_dict['cards'] += [old] * 30
    # deck = Deck(**deck_dict)
    # change HP
    # for charactor in deck.charactors:
    #     charactor.hp = 2
    #     charactor.max_hp = 2
    if seed:
        match: Match = Match(random_state = seed)
    else:
        match: Match = Match()
    match.set_deck([deck, deck])
    match.config.max_same_card_number = None
    match.config.charactor_number = None
    match.config.card_number = None
    match.config.random_first_player = False
    if rich:
        set_16_omni(match)
    match.start()
    match.step()
    if agent_0.__class__ != InteractionAgent:
        while match.need_respond(0):
            make_respond(agent_0, match)
    return match


agent_0 = NothingAgent(player_idx = 0)
agent_0 = InteractionAgent(player_idx = 0, only_use_command = True)
agent_1 = InteractionAgent(player_idx = 1, only_use_command = True)


@app.on_event('startup')
async def startup_event():
    global match
    match = get_new_match(seed = get_random_state(), rich = True)


@app.post('reset')
async def reset(fixed_random_seed: bool = False, offset: int = 0, 
                rich: bool = False):
    global match
    if fixed_random_seed:
        random_seed = get_random_state(offset)
    else:
        random_seed = None
    match = get_new_match(seed = random_seed, rich = rich)


@app.get('/state/{player_idx}')
async def get_game_state(player_idx: int):
    if player_idx < 0 or player_idx > 1:
        raise HTTPException(status_code = 404, detail = 'Player not found')
    if player_idx == 0:
        raise HTTPException(status_code = 404, 
                            detail = 'player 0 not suppoted')
    return JSONResponse(match.dict())


class RespondData(BaseModel):
    player_idx: int
    command: str


@app.post('/respond')
async def post_respond(data: RespondData):
    player_idx = data.player_idx
    command = data.command
    if not match.need_respond(player_idx):
        raise HTTPException(status_code = 404, detail = 'Not your turn')
    if player_idx == 0:
        agent = agent_0
    elif player_idx == 1:
        agent = agent_1
    else:
        raise HTTPException(status_code = 404, detail = 'Player not found')
    if agent.__class__ == NothingAgent:
        raise HTTPException(status_code = 404, 
                            detail = 'Cannot control this agent')
    agent.commands = [command]
    resp = agent.generate_response(match)
    if resp is None:
        raise HTTPException(status_code = 404, detail = 'Invalid command')
    match.respond(resp)
    match.step()
    for agent in (agent_0, agent_1):
        if (
            agent.__class__ != InteractionAgent 
            or len(agent.commands) > 0  # type: ignore
        ):
            while match.need_respond(agent.player_idx):
                make_respond(agent, match)
    return JSONResponse(match.dict())
