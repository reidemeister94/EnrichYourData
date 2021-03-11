import bcrypt
from pymongo import MongoClient
import os
import sys


def insert_user(username, password):
    mongourl = os.environ["MONGO_URL"]
    mongo_client = MongoClient(mongourl)

    # username = "username"
    # password = "password"
    password = str.encode(password)
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())

    # print(hashed)
    collection = mongo_client["users"]["credentials"]
    try:
        collection.insert_one({"username": username, "password": hashed})
        print("inserted")
    except:
        print("error on inserting user")


if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2]
    insert_user(username, password)
