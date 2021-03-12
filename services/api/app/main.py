from typing import Optional
import os
import ast
import json
from fastapi import Security, Depends, FastAPI, HTTPException, Form, status
from fastapi.security.api_key import APIKeyQuery, APIKeyCookie, APIKeyHeader, APIKey
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager  # Loginmanager Class
from fastapi_login.exceptions import InvalidCredentialsException  # Exception class
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
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

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates/")
db_handler = DBHandler()
SECRET = os.urandom(24).hex()
# To obtain a suitable secret key you can run | import os; print()

manager = LoginManager(SECRET, tokenUrl="/auth/token", use_cookie=True)
manager.cookie_name = "authc"

# hashed = bcrypt.hashpw(password, bcrypt.gensalt())
# if bcrypt.checkpw(password, hashed):
#     print("It Matches!")


class NotAuthenticatedException(Exception):
    pass


manager.not_authenticated_exception = NotAuthenticatedException

# these two argument are mandatory
def exc_handler(request, exc):
    return RedirectResponse(url="/login")


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


@app.get("/test")
def read_root(request: Request):
    collection = db_handler.MONGO_CLIENT["tweets"]["test"]
    collection.insert_one(
        {
            "title": "test" + str(random.randint(1000000, 9999999)),
            "text": "".join(
                random.choices(
                    string.ascii_uppercase + string.digits, k=random.randint(10, 50)
                )
            ),
        }
    )
    return {"Your IP is": request.client.host}


@app.get("/")
def read_root(api_key: APIKey = Depends(get_api_key), client_ip=Depends(get_client_ip)):
    return {"Hi": API_KEYS[api_key], "Your IP": client_ip}


@manager.user_loader
def load_user(username: str):
    user = db_handler.check_username(username)
    return user


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": False})


@app.post("/login/error", response_class=HTMLResponse)
async def login_page_error(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": True})


@app.post("/send_tweet")
def update_tweet(radio_label=Form(...), _=Depends(manager)):
    radio_label = int(radio_label)
    if radio_label == 1:
        return "Pro Vax"
    elif radio_label == 2:
        return "No Vax"
    elif radio_label == 3:
        return "Neutral"
    else:
        return "Out of context"


@app.post("/auth/token")
def login(data: OAuth2PasswordRequestForm = Depends()):
    username = data.username
    password = str.encode(data.password)
    if len(username) == 0 or len(password) == 0:
        raise InvalidCredentialsException
    user = load_user(username)
    if not user or (not bcrypt.checkpw(password, user["password"])):
        print("ROBA SBAGLIATA")
        return RedirectResponse(url="/login/error")
    else:
        access_token = manager.create_access_token(
            data={"sub": username}, expires=timedelta(hours=12)
        )
        resp = RedirectResponse(url="/labeling", status_code=status.HTTP_302_FOUND)
        manager.set_cookie(resp, access_token)
        return resp


@app.get("/labeling", response_class=HTMLResponse)
def get_private_endpoint(request: Request, _=Depends(manager)):
    return templates.TemplateResponse("tweet.html", {"request": request})


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