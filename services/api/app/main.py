from typing import Optional
import os
import ast
import json
from fastapi import Security, Depends, FastAPI, HTTPException
from fastapi.security.api_key import APIKeyQuery, APIKeyCookie, APIKeyHeader, APIKey
from starlette.requests import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_403_FORBIDDEN
from db.db_handler import DBHandler
from visualization.bokeh_handler import BokehHandler


API_KEY_NAME = "access_token"
API_KEYS = ast.literal_eval(os.environ["API_KEYS"])
ALLOWED_IP_LIST = os.environ["ALLOWED_IPS"].split(",")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

app = FastAPI()
db_handler = DBHandler()


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
    return {"Your IP is": request.client.host}


@app.get("/")
def read_root(api_key: APIKey = Depends(get_api_key), client_ip=Depends(get_client_ip)):
    return {"Hi": API_KEYS[api_key], "Your IP": client_ip}


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