import bcrypt
from pymongo import MongoClient
import os
import sys
from hashlib import sha256


def insert_user(username, password):
    mongourl = os.environ["MONGO_URL"]
    mongo_client = MongoClient(mongourl)

    # username = "username"
    # password = "password"
    username = sha256(str.encode(username)).hexdigest()

    password = str.encode(password)
    hashed_pwd = bcrypt.hashpw(password, bcrypt.gensalt())

    # print(hashed)
    collection = mongo_client["users"]["credentials"]
    try:
        collection.insert_one({"username": username, "password": hashed_pwd})
        print("inserted")
    except:
        print("error on inserting user")


if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2]
    insert_user(username, password)
