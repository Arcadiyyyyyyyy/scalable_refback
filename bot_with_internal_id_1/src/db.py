from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

from dotenv import load_dotenv
from typing import Any, Mapping

from .static.const import CsvColumns, MinimumWithdrawValues, Other

import logging
import os


load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

if MONGO_URI is None:
    logging.critical("DB URI not found. Check .env")
else:
    client: MongoClient[Mapping[str, Any] | Any] = MongoClient(MONGO_URI)
    logging.info("Connected to the db successfully")
    bot_db: Database[Mapping[str, Any] | Any] = client["refback_bot_with_id_1"]
    api_db: Database[Mapping[str, Any] | Any] = client["refback_api"]

    chat_collection = bot_db["chat"]
    support_tickets_collection = bot_db["support_tickets"]
    support_messages_collection = bot_db["support_messages"]
    restrictions_collection = bot_db["restrictions"]

    csv_cache_collection = api_db["csv_cache"]


def create_chat(chat_id: int, **kwargs):
    logging.debug("Checking if chat with id {:} exists".format(chat_id))
    chat = read_chat(chat_id)
    if chat is None:
        logging.debug("Started creating chat with id {:}".format(chat_id))

        arguments = {
            "chat_id": chat_id,
            "language": "ru",
            "user_level": 1,
            "first_interaction": datetime.now(),
            "available_to_withdraw_usdt": 0.0,
            "available_to_withdraw_bnb": 0.0
        }

        result = chat_collection.insert_one(
            {**arguments, **kwargs}
        )
        logging.debug("Finished creating chat with id {:}".format(chat_id))
    else:
        logging.debug("Chat with id {:} already exists, skipped".format(chat_id))
        return

    return result


def read_chat(chat_id: int):
    logging.debug("Started reading chat with id {:}".format(chat_id))
    result = chat_collection.find_one({"chat_id": chat_id}, {})
    logging.debug("Finished reading chat with id {:}".format(chat_id))

    return result


def change_chat_language(chat_id: int, new_lang_code: str):
    logging.debug("Started changing chat language in id {:} to {:}".format(chat_id, new_lang_code))
    result = chat_collection.update_one({"chat_id": chat_id}, {"$set": {"language": new_lang_code}})
    logging.debug("Finished changing chat language in id {:} to {:}".format(chat_id, new_lang_code))

    return result


def create_support_ticket(chat_id: int, heading: str):
    return support_tickets_collection.insert_one(
        {
            "chat_id": chat_id,
            "heading": heading,
            "is_selected_by_user": True,
            "selected_by_support": None,
            "state": "new",
            "created_at": datetime.utcnow(),
        }
    )


def read_open_tickets(chat_id: int):
    """Finds all open user tickets"""
    return support_tickets_collection.find(
        {"chat_id": chat_id, "state": {"$ne": "closed"}}, {}
    )


def read_ticket(_id: ObjectId | str):
    return support_tickets_collection.find_one(
        {"_id": _id if type(_id) == ObjectId else ObjectId(_id)}
    )


def read_selected_ticket(chat_id: int, from_type, **kwargs):
    if from_type not in ["user", "support_agent"]:
        raise Exception("Unknown user_type")

    _chat_id = "chat_id" if from_type == "user" else "support_agent"
    _is_selected_by = (
        "is_selected_by_user" if from_type == "user" else "selected_by_support"
    )

    return support_tickets_collection.find_one(
        {
            _chat_id: chat_id,
            "state": "in_progress",
            _is_selected_by: True if from_type == "user" else chat_id,
        },
        kwargs,
    )


def read_all_admins(level: int):
    """Finds all admins that are higher than level x"""
    return chat_collection.find({"admin_level": {"$gte": level}}, {})


def read_all_new_tickets():
    """Finds all tickets with a status new (used for admins)"""
    return support_tickets_collection.find({"state": "new"}, {})


def read_agent_tickets(tg_id: int, list_closed=False, **kwargs):
    """Finds all tickets managed by selected support agent"""
    params = {"support_agent": tg_id}

    if not list_closed:
        params["state"] = {"$ne": "closed"}

    return support_tickets_collection.find(params, kwargs)


def close_support_ticket(ticket_id: str | ObjectId):
    return support_tickets_collection.update_one(
        {
            "_id": ObjectId(ticket_id) if type(ticket_id) == str else ticket_id,
            "state": {"$ne": "closed"},
        },
        {
            "$set": {
                "state": "closed",
                "closed_at": datetime.utcnow(),
                "is_selected_by_user": False,
                "selected_by_support": None,
            }
        },
    )


def unselect_all_tickets(user_tg_id: int, side):
    return support_tickets_collection.update_many(
        {
            "state": {"$ne": "closed"},
            "chat_id" if side == "user" else "support_agent": user_tg_id,
        },
        {
            "$set": {
                "is_selected_by_user"
                if side == "user"
                else "selected_by_support": False
                if side == "user"
                else None
            }
        },
    )


def select_support_ticket(ticket_id: str | ObjectId, user_tg_id: int, side: str):
    """Selects given ticket, unselects all others"""
    unselect_all_tickets(user_tg_id, side)

    return support_tickets_collection.update_one(
        {
            "_id": ObjectId(ticket_id) if type(ticket_id) == str else ticket_id,
            "state": {"$ne": "closed"},
        },
        {
            "$set": {
                "is_selected_by_user"
                if side == "user"
                else "selected_by_support": True
                if side == "user"
                else user_tg_id
            }
        },
    )


def assign_ticket_to_support_agent(support_agent_tg_id: int, ticket_id: ObjectId | str):
    """Changes state of the selected ticket, as well as adds a value that leads to current support agent that's
    responsible for this ticket"""
    return support_tickets_collection.update_one(
        {
            "_id": ObjectId(ticket_id) if type(ticket_id) == str else ticket_id,
            "state": "new",
        },
        {"$set": {"state": "in_progress", "support_agent": support_agent_tg_id}},
    )


def add_message_to_the_ticket(formatted_message, chat_id, from_type):
    if from_type not in ["user", "support_agent"]:
        raise Exception("Unknown user_type")

    ticket = read_selected_ticket(chat_id, from_type)

    return support_messages_collection.insert_one(
        {
            "ticket_id": ticket.get("_id"),
            "issuer_tg_id": ticket.get("chat_id"),
            **formatted_message,
        }
    )


def read_ticket_messages(chat_id, from_type, reverse=False):
    if from_type not in ["user", "support_agent"]:
        raise Exception("Unknown user_type")

    ticket = read_selected_ticket(chat_id, from_type)

    return support_messages_collection.find(
        {"ticket_id": ticket.get("_id"), "issuer_tg_id": ticket.get("chat_id")}, {}
    ).sort("date", 1 if not reverse else -1)


def update_tg_nicknames(tg_id: int, name: str, username: str):
    return chat_collection.update_one({"chat_id": tg_id}, {"$set": {"tg_name": name, "tg_link": username}})


def update_registered_user(tg_id: int, real_name: str, bid: int, wallet: str):
    return chat_collection.update_one(
        {"chat_id": tg_id},
        {
            "$set": {
                "real_name": real_name,
                "binance_id": bid,
                "withdraw_wallet": wallet,
                "full_registration_time": datetime.utcnow()
            }
        }
    )


def update_profit_values_by_tg_id(tg_id: int, usdt: float, bnb: float):
    return chat_collection.update_one(
        {"chat_id": tg_id},
        {
            "$set": {
                "available_to_withdraw_usdt": usdt,
                "available_to_withdraw_bnb": bnb
            }
        }
    )


def prune_withdraw_records():
    return chat_collection.update_many(
        {
            "$or": [
                {
                    "available_to_withdraw_usdt": {
                        "$gte": MinimumWithdrawValues.usdt.value
                    }
                },
                {
                    "available_to_withdraw_bnb": {
                        "$gte": MinimumWithdrawValues.bnb.value
                    }
                }
            ]
        },
        {
            "$set": {
                "available_to_withdraw_usdt": 0.0,
                "available_to_withdraw_bnb": 0.0
            }
        }
    )


def read_all_users_with_not_null_withdraw_amounts():
    return chat_collection.find(
        {
            "$or": [
                {
                    "available_to_withdraw_usdt": {
                        "$gte": MinimumWithdrawValues.usdt.value
                    }
                },
                {
                    "available_to_withdraw_bnb": {
                        "$gte": MinimumWithdrawValues.bnb.value
                    }
                }
            ]
        }
    ).sort("available_to_withdraw_usdt", -1)


def read_bid(bid: int):
    return chat_collection.find_one({"binance_id": bid})


def write_lines_from_csv(bot_internal_id: int, string_csv_rows: str):
    list_csv_rows = string_csv_rows.split("\n")
    documents_to_insert = []
    for row in list_csv_rows:
        line_elements: list = row.split(",")
        if len(line_elements) > 1 and line_elements[1].replace(".", "").isdigit() is True:
            documents_to_insert.append(
                {
                    CsvColumns.order_type.value: line_elements[0],
                    CsvColumns.friend_id_spot.value: int(line_elements[1]),
                    CsvColumns.friend_id_sub_spot.value: line_elements[2],
                    CsvColumns.commission_asset.value: line_elements[3],
                    CsvColumns.coin_commission_earned.value: float(line_elements[4]),
                    CsvColumns.usdt_commission_earned.value: float(line_elements[5]),
                    CsvColumns.commission_time.value: datetime.strptime(line_elements[6], "%Y-%m-%d %H:%M:%S"),
                    CsvColumns.registration_time.value: datetime.strptime(line_elements[7], "%Y-%m-%d %H:%M:%S"),
                    CsvColumns.referral_id.value: str(line_elements[8]).rstrip("\n"),
                    "Internal ID": bot_internal_id,
                    "Date of trial end": datetime.strptime(line_elements[7], "%Y-%m-%d %H:%M:%S") + timedelta(30)
                }
            )

    return csv_cache_collection.insert_many(documents_to_insert)


def increase_level(binance_id: int):
    user = read_bid(binance_id)
    if user is None:
        return
    current_level = user.get("user_level", 1)
    if current_level < Other.maximum_user_level.value:
        return chat_collection.update_one({"binance_id": binance_id}, {"$set": {"user_level": current_level + 1}})


def decrease_level(binance_id: int):
    user = read_bid(binance_id)
    if user is None:
        return
    current_level = user.get("user_level", 1)
    if current_level > 1:
        return chat_collection.update_one({"binance_id": binance_id}, {"$set": {"user_level": current_level - 1}})


# TODO: add the ability to add admins of different levels
def add_new_admin():
    raise NotImplementedError


def read_restrictions_for_tg_id(chat_id: int):
    return restrictions_collection.find_one({"chat_id": chat_id}, {})
