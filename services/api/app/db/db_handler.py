import collections
from posix import listdir
import pymongo
from pymongo import MongoClient
from pymongo.errors import CursorNotFound, ServerSelectionTimeoutError
import os
import time
import logging
import yaml
import sys
import gc
import pprint
import datetime
from dateutil.relativedelta import relativedelta
import re
import dateutil.parser as parser
from datetime import timezone
from hashlib import sha256


class DBHandler:
    def __init__(self):
        self.LOGGER = self.__get_logger()
        mongourl = os.environ["MONGO_URL"]
        self.MONGO_CLIENT = MongoClient(mongourl)
        self.db_users = os.environ["MONGO_USERS_DB"]
        self.collection_users = os.environ["MONGO_USERS_COLLECTION"]

    def get_common_words(self, start_date, lang):
        if type(start_date) is str:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = start_date + relativedelta(months=1) - datetime.timedelta(days=1)
        collection = self.MONGO_CLIENT["statistics"]["month_" + lang]
        ts = int(end_date.replace(tzinfo=timezone.utc).timestamp())
        query = {"ts": ts}
        documents = collection.find(query)
        if documents is not None:
            res = {"data": []}
            for doc in documents:
                date_range = doc["dateRange"]
                date_range = date_range.split("00:00:00-")
                for i in range(len(date_range)):
                    date_range[i] = date_range[i].replace("00:00:00", "").strip()
                res["data"].append(
                    {
                        "date_range": "{}__{}".format(date_range[0], date_range[1]),
                        "most_frequent_words": doc["most_frequent_words"],
                    }
                )
            return res
        return None

    def get_articles_per_day(self, start_date, lang):
        try:
            if type(start_date) is str:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m")
            # self.LOGGER.info(start_date)
            end_date = start_date + relativedelta(months=1) - datetime.timedelta(days=1)
            # self.LOGGER.info(end_date)
            if lang == "it":
                collection = self.MONGO_CLIENT["news"]["article"]
            else:
                collection = self.MONGO_CLIENT["news"]["article_" + lang]

            documents = collection.aggregate(
                [
                    {"$match": {"discoverDate": {"$gte": start_date, "$lte": end_date}}},
                    {
                        "$group": {
                            "_id": {
                                "$dateToString": {
                                    "format": "%Y-%m-%d",
                                    "date": "$discoverDate",
                                }
                            },
                            "count": {"$sum": 1},
                        }
                    },
                    {
                        "$sort": {
                            "_id": pymongo.ASCENDING,
                        }
                    },
                ]
            )

            date_db = []
            count_db = []

            for doc in documents:
                date_db.append(datetime.datetime.strptime(doc["_id"], "%Y-%m-%d"))
                count_db.append(doc["count"])

            data = dict(date=date_db, count=count_db)
            return data
        except Exception as e:
            exc_type, _, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self.LOGGER.error(
                "{}, {}, {}, {}, {}".format(
                    start_date, exc_type, fname, exc_tb.tb_lineno, str(e)
                )
            )
            return None

    def get_reduced_articles(self, start_date, lang):
        try:
            if type(start_date) is str:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m")
            # self.LOGGER.info(start_date)
            end_date = start_date + relativedelta(months=1) - datetime.timedelta(days=1)
            # self.LOGGER.info(end_date)
            if lang == "it":
                collection = self.MONGO_CLIENT["news"]["article"]
            else:
                collection = self.MONGO_CLIENT["news"]["article_" + lang]

            query = {"discoverDate": {"$gte": start_date, "$lte": end_date}}

            documents = collection.find(query, no_cursor_timeout=True)

            x_db = []
            y_db = []
            date_db = []
            title_db = []
            topic_db = []

            for doc in documents:
                if len(doc["reducedEmbedding"]) > 0:
                    x_db.append(doc["reducedEmbedding"][0])
                    y_db.append(doc["reducedEmbedding"][1])
                    date_db.append(doc["discoverDate"])
                    title_db.append(doc["title"])
                    topic_db.append(doc["topicExtraction"])

            data = dict(x=x_db, y=y_db, date=date_db, title=title_db, topic=topic_db)
            return data
        except Exception as e:
            exc_type, _, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self.LOGGER.error(
                "{}, {}, {}, {}, {}".format(
                    start_date, exc_type, fname, exc_tb.tb_lineno, str(e)
                )
            )
            return None

    def get_sample_tweet(self, user):
        try:
            sample_tweet = (
                self.MONGO_CLIENT[os.environ["MONGO_DATA_DB"]][
                    os.environ["MONGO_DATA_COLLECTION"]
                ]
                .aggregate(
                    [
                        {
                            "$match": {
                                "label_final": {"$exists": False},
                                "labels.user": {"$ne": user},
                                "count": {"$not": {"$gt": 2}, "$gt": 0},
                            }
                        },
                        {"$sample": {"size": 1}},
                    ]
                )
                .next()
            )
            return sample_tweet
        except:
            sample_tweet = (
                self.MONGO_CLIENT[os.environ["MONGO_DATA_DB"]][
                    os.environ["MONGO_DATA_COLLECTION"]
                ]
                .aggregate(
                    [
                        {
                            "$match": {
                                "label_final": {"$exists": False},
                                "labels.user": {"$ne": user},
                                "count": {"$not": {"$gt": 2}},
                            }
                        },
                        {"$sample": {"size": 1}},
                    ]
                )
                .next()
            )
            return sample_tweet

    #     try:
    #         sample_tweet = (
    #             self.MONGO_CLIENT[os.environ["MONGO_DATA_DB"]][
    #                 os.environ["MONGO_DATA_COLLECTION"]
    #             ]
    #             .aggregate(
    #                 [
    #                     {
    #                         "$match": {
    #                             "label": {"$exists": False},
    #                             # "retweeted_status": {"$exists": False},
    #                             "lang": "it",
    #                         }
    #                     },
    #                     {"$sample": {"size": 1}},
    #                 ]
    #             )
    #             .next()
    #         )
    #         return sample_tweet
    #     except Exception as e:
    #         exc_type, _, exc_tb = sys.exc_info()
    #         fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    #         self.LOGGER.error(
    #             "{}, {}, {}, {}".format(exc_type, fname, exc_tb.tb_lineno, str(e))
    #         )
    #         return {"id": 0, "full_text": ""}

    def check_username(self, username):
        credentials_coll = self.MONGO_CLIENT[self.db_users][self.collection_users]
        username = sha256(str.encode(username)).hexdigest()
        user_db = credentials_coll.find_one({"username": username})
        if user_db is None:
            return None
        else:
            return {"password": user_db["password"]}

    def __get_logger(self):
        # create logger
        logger = logging.getLogger("DBHandler")
        logger.setLevel(logging.DEBUG)
        # create console handler and set level to debug
        log_path = "db/log/db_handler.log"
        if not os.path.isdir("db/log/"):
            os.mkdir("db/log/")
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.DEBUG)
        # create formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return logger
