import logging
import os
from typing import Mapping, Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

from .static.db_search_models import CommissionAsset, OrderType, CsvColumns


load_dotenv()
MONGO_URI = os.getenv("MONGODB_CONNECTION")

if MONGO_URI is None:
    logging.critical("DB URI not found. Check .env")
else:
    client: MongoClient = MongoClient(MONGO_URI)
    logging.info("Connected to the db successfully")
    api_db: Database[Mapping[str, Any] | Any] = client["refback_api"]

    csv_cache_collection = api_db["csv_cache"]


def read_transaction_from_cached_csv_by_bid(bid: int):
    return csv_cache_collection.find_one({CsvColumns.friend_id_spot.value: bid})


def read_all_used_buids_in_cached_csv():
    return csv_cache_collection.distinct(CsvColumns.friend_id_spot.value)


def aggregate_cached_csv(
        bot_internal_id: int,
        order_type: str,
        commission_asset: str,
        less_or_more_than_30_days_from_registration: str
):
    if less_or_more_than_30_days_from_registration not in ["lt", "gte"]:
        raise Exception("Input error")
    if order_type not in [x.value for x in OrderType]:
        raise Exception("Input error")
    if commission_asset not in [x.value for x in CommissionAsset]:
        raise Exception("Input error")

    return csv_cache_collection.aggregate(
        [
            {
                "$match": {
                    "Internal ID": bot_internal_id,
                    CsvColumns.order_type.value: order_type,
                    CsvColumns.commission_asset.value: commission_asset,
                }
            },
            {
                "$match": {
                    "$expr": {
                        "$"+less_or_more_than_30_days_from_registration: [
                            '$'+CsvColumns.commission_time.value, '$'+"Date of trial end"
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$"+CsvColumns.friend_id_spot.value,
                    "USDT_COMMISSION_SUM": {
                        "$sum": "$"+CsvColumns.usdt_commission_earned.value
                    },
                    "COIN_COMMISSION_SUM": {
                        "$sum": "$"+CsvColumns.coin_commission_earned.value
                    }
                }
            },
        ]
    )


def prune_cached_csv(bot_internal_id: int):
    return csv_cache_collection.delete_many({"Internal ID": bot_internal_id})
