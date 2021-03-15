import datetime
from typing import Optional
import os
import ast
import json
from fastapi import Security, Depends, FastAPI, HTTPException, Form, status, Response
from fastapi.security.api_key import APIKeyQuery, APIKeyCookie, APIKeyHeader, APIKey
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager  # Loginmanager Class
from fastapi_login.exceptions import InvalidCredentialsException  # Exception class
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_403_FORBIDDEN
from db.db_handler import DBHandler
from visualization.bokeh_handler import BokehHandler
import random
import string
from pymongo import MongoClient
import bcrypt
from datetime import timedelta


API_KEY_NAME = "access_token"
API_KEYS = ast.literal_eval(os.environ["API_KEYS"])
ALLOWED_IP_LIST = os.environ["ALLOWED_IPS"].split(",")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates/")
db_handler = DBHandler()
SECRET = os.urandom(24).hex()
login_url = os.environ["LOGIN_URL"]
auth_url = os.environ["AUTH_URL"]
labeling_url = os.environ["LABEL_URL"]
send_tweet_url = os.environ["SEND_TWEET_URL"]
# To obtain a suitable secret key you can run | import os; print()

manager = LoginManager(SECRET, tokenUrl=auth_url, use_cookie=True)
manager.cookie_name = "authc"

# hashed = bcrypt.hashpw(password, bcrypt.gensalt())
# if bcrypt.checkpw(password, hashed):
#     print("It Matches!")


class NotAuthenticatedException(Exception):
    pass


manager.not_authenticated_exception = NotAuthenticatedException

# these two argument are mandatory
def exc_handler(request, exc):
    return RedirectResponse(url="/{}".format(login_url), status_code=status.HTTP_302_FOUND)


# You also have to add an exception handler to your app instance
app.add_exception_handler(NotAuthenticatedException, exc_handler)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header in API_KEYS:
        return api_key_header
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not Authorized")


async def get_client_ip(request: Request):
    if request.client.host in ALLOWED_IP_LIST:
        return request.client.host
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not Authorized")


# @app.get("/test")
# def read_root(request: Request):
#     collection = db_handler.MONGO_CLIENT["tweets"]["test"]
#     collection.insert_one(
#         {
#             "title": "test" + str(random.randint(1000000, 9999999)),
#             "text": "".join(
#                 random.choices(
#                     string.ascii_uppercase + string.digits, k=random.randint(10, 50)
#                 )
#             ),
#         }
#     )
#     return {"Your IP is": request.client.host}


# @app.get("/")
# def read_root(api_key: APIKey = Depends(get_api_key), client_ip=Depends(get_client_ip)):
#     return {"Hi": API_KEYS[api_key], "Your IP": client_ip}


@manager.user_loader
def load_user(username: str):
    user = db_handler.check_username(username)
    return user


### login_polimi
@app.get("/{}".format(login_url), response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "auth": auth_url, "error": False}
    )


@app.post("/{}/error".format(login_url), response_class=HTMLResponse)
async def login_page_error(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "auth": auth_url, "error": True}
    )


@app.get("/{}/error".format(login_url), response_class=HTMLResponse)
async def redirect_login_page_error(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "auth": auth_url, "error": False}
    )


# send_tweet_polimi
@app.post(send_tweet_url + "/{tweet_id}")
def update_tweet(tweet_id: int, radio_label=Form(...), _=Depends(manager)):
    query = {"id": tweet_id}
    new_value = {"$set": {"label": int(radio_label)}}
    db_handler.MONGO_CLIENT[os.environ["MONGO_DATA_DB"]][
        os.environ["MONGO_DATA_COLLECTION"]
    ].update_one(query, new_value)
    return RedirectResponse(url=labeling_url, status_code=status.HTTP_302_FOUND)


# auth_polimi
@app.post(auth_url)
def login(username=Form(...), password=Form(...)):
    username = username.lower()
    password = str.encode(password)
    user = load_user(username)
    if not user or (not bcrypt.checkpw(password, user["password"])):
        return RedirectResponse(url="/{}/error".format(login_url))
    else:
        access_token = manager.create_access_token(
            data={"sub": username}, expires=timedelta(hours=12)
        )
        resp = RedirectResponse(url=labeling_url, status_code=status.HTTP_302_FOUND)
        manager.set_cookie(resp, access_token)
        return resp


# labeling_polimi
@app.get(labeling_url, response_class=HTMLResponse)
def get_private_endpoint(request: Request, _=Depends(manager)):
    # sample_tweet = db_handler.MONGO_CLIENT[os.environ["MONGO_DATA_DB"]][
    #     os.environ["MONGO_DATA_COLLECTION"]
    # ].find_one({"label": {"$exists": False}, "retweeted_status": {"$exists": False}})
    sample_tweet = db_handler.get_sample_tweet()
    return templates.TemplateResponse(
        "tweet.html",
        {
            "request": request,
            "tweet_text": sample_tweet["full_text"],
            "tweet_id": sample_tweet["id"],
            "send_tweet_url": send_tweet_url,
        },
    )


@app.get("/common_words")
async def common_words(
    request: Request,
    date: str,
    lang: str,
    api_key: APIKey = Depends(get_api_key),
    client_ip=Depends(get_client_ip),
):
    if "date" not in request.query_params or "lang" not in request.query_params:
        raise HTTPException(status_code=400, detail="Bad Request")
    else:
        common_words = db_handler.get_common_words(date, lang)
        if common_words is not None:
            response_json = jsonable_encoder(common_words)
            response = JSONResponse(content=response_json)
            return response
        else:
            return "Something went wrong"
