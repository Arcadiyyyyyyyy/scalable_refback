import json
import os

import i18n
import requests
from telegram import Update
from telegram.ext import CallbackContext, Application

from .db import read_chat, update_tg_nicknames, read_bid, update_profit_values_by_tg_id, \
    read_all_users_with_not_null_withdraw_amounts, read_restrictions_for_tg_id
from .static.const import CommandsWithDescriptions, CommandsRelated, WithdrawCommissions, MinimumWithdrawValues, Other
from .static import formulas
from .static.formulas import formula_for_total_volume_calculation_before_30_days, \
    formula_for_total_volume_calculation_after_30_days


def is_chat_exists(chat_id) -> bool:
    return True if read_chat(chat_id) is not None else False


def main_handler(chat_id, name, user):
    if name is not None and user is not None:
        update_tg_nicknames(chat_id, name, user)
    return language_handler(chat_id)


def critical_checks(chat_id: int) -> bool:
    restrictions = read_restrictions_for_tg_id(chat_id)
    if chat_id <= 0:
        return False
    elif restrictions is not None and restrictions:
        return False
    else:
        return True


def language_handler(chat_id):
    chat = read_chat(chat_id)
    try:
        i18n.set("locale", chat["language"])
    except KeyError:
        pass
    return chat.get("language", "en")


def is_chat_private(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.type == "private":
        return True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=i18n.t("translation.the_chat_is_not_private"),
        )
        return False


def is_admin(update: Update | int, required_level):
    """If you can't get update(from jobs), please, send chat_id in update field"""
    if type(update) == Update:
        main_handler(
            update.effective_chat.id if type(update) == Update else update,
            update.effective_user.first_name,
            update.effective_user.username
        )
    chat = read_chat(update.effective_chat.id if type(update) == Update else update)
    return (
        True
        if chat.get("admin_level") is not None
        and chat.get("admin_level") >= required_level
        else False
    )


async def generate_command_list(application: Application):
    command_list = []
    for x in [command.value for command in CommandsWithDescriptions]:
        command_list.append(
            (x.get(CommandsRelated.command_name.value), x.get(CommandsRelated.command_description.value))
        )
    await application.bot.set_my_commands(command_list)


def is_fully_registered(chat_id: int):
    return True if read_chat(chat_id).get("authorization_time") is not None else False


def calculate_cashback_for_user_with_id(sum_from_api: dict, bid: int):
    user = read_bid(bid)
    # print(bid, user)
    # print(sum_from_api)

    if user is None:
        return

    user_level = user.get("user_level", 1)

    """Before goes for before 30 days of using the bot, after goes for after using bot for 30 days. s_ goes for sum"""
    _before = sum_from_api.get("sum_results_before_user_used_the_bot_for_30_days", {})
    _after = sum_from_api.get("sum_results_after_user_used_the_bot_for_30_days", {})
    _spot = "spot"
    _futures = "futures"
    _before_spot = _before.get(_spot, {})
    _before_futures = _before.get(_futures, {})
    _after_spot = _after.get(_spot, {})
    _after_futures = _after.get(_futures, {})

    before_spot_usdt = _before_spot.get("usdt", 0.0)
    before_spot_busd = _before_spot.get("busd", 0.0)
    before_spot_bnb = _before_spot.get("bnb", 0.0)
    before_futures_usdt = _before_futures.get("usdt", 0.0)
    before_futures_busd = _before_futures.get("busd", 0.0)
    before_futures_bnb = _before_futures.get("bnb", 0.0)
    after_spot_usdt = _after_spot.get("usdt", 0.0)
    after_spot_busd = _after_spot.get("busd", 0.0)
    after_spot_bnb = _after_spot.get("bnb", 0.0)
    after_futures_usdt = _after_futures.get("usdt", 0.0)
    after_futures_busd = _after_futures.get("busd", 0.0)
    after_futures_bnb = _after_futures.get("bnb", 0.0)

    del _before
    del _after
    del _spot
    del _futures
    del _before_spot
    del _before_futures
    del _after_spot
    del _after_futures

    if user_level == 1:
        calculated_before_spot_usdt = formulas.level1_spot_less30(before_spot_usdt)
        calculated_before_spot_busd = formulas.level1_spot_less30(before_spot_busd)
        calculated_before_spot_bnb = formulas.level1_bnb_less30(before_spot_bnb)
        calculated_before_futures_usdt = formulas.level1_futures_less30(before_futures_usdt)
        calculated_before_futures_busd = formulas.level1_futures_less30(before_futures_busd)
        calculated_before_futures_bnb = formulas.level1_bnb_less30(before_futures_bnb)
        calculated_after_spot_usdt = formulas.level1_spot_more30(after_spot_usdt)
        calculated_after_spot_busd = formulas.level1_spot_more30(after_spot_busd)
        calculated_after_spot_bnb = formulas.level1_bnb_more30(after_spot_bnb)
        calculated_after_futures_usdt = formulas.level1_futures_more30(after_futures_usdt)
        calculated_after_futures_busd = formulas.level1_futures_more30(after_futures_busd)
        calculated_after_futures_bnb = formulas.level1_bnb_more30(after_futures_bnb)

    elif user_level == 2:
        calculated_before_spot_usdt = formulas.level2_spot_less30(before_spot_usdt)
        calculated_before_spot_busd = formulas.level2_spot_less30(before_spot_busd)
        calculated_before_spot_bnb = formulas.level2_bnb_less30(before_spot_bnb)
        calculated_before_futures_usdt = formulas.level2_futures_less30(before_futures_usdt)
        calculated_before_futures_busd = formulas.level2_futures_less30(before_futures_busd)
        calculated_before_futures_bnb = formulas.level2_bnb_less30(before_futures_bnb)
        calculated_after_spot_usdt = formulas.level2_spot_more30(after_spot_usdt)
        calculated_after_spot_busd = formulas.level2_spot_more30(after_spot_busd)
        calculated_after_spot_bnb = formulas.level2_bnb_more30(after_spot_bnb)
        calculated_after_futures_usdt = formulas.level2_futures_more30(after_futures_usdt)
        calculated_after_futures_busd = formulas.level2_futures_more30(after_futures_busd)
        calculated_after_futures_bnb = formulas.level2_bnb_more30(after_futures_bnb)

    else:
        calculated_before_spot_usdt = 0.0
        calculated_before_spot_busd = 0.0
        calculated_before_spot_bnb = 0.0
        calculated_before_futures_usdt = 0.0
        calculated_before_futures_busd = 0.0
        calculated_before_futures_bnb = 0.0
        calculated_after_spot_usdt = 0.0
        calculated_after_spot_busd = 0.0
        calculated_after_spot_bnb = 0.0
        calculated_after_futures_usdt = 0.0
        calculated_after_futures_busd = 0.0
        calculated_after_futures_bnb = 0.0

    del before_spot_usdt
    del before_spot_busd
    del before_spot_bnb
    del before_futures_usdt
    del before_futures_busd
    del before_futures_bnb
    del after_spot_usdt
    del after_spot_busd
    del after_spot_bnb
    del after_futures_usdt
    del after_futures_busd
    del after_futures_bnb

    total_usdt = sum(
        [
            calculated_after_spot_usdt,
            calculated_after_futures_usdt,
            calculated_before_futures_usdt,
            calculated_before_spot_usdt,

            calculated_before_spot_busd,
            calculated_before_futures_busd,
            calculated_after_spot_busd,
            calculated_after_futures_busd
        ]
    )
    total_bnb = sum(
        [
            calculated_after_futures_bnb,
            calculated_before_futures_bnb,
            calculated_after_spot_bnb,
            calculated_before_spot_bnb
        ]
    )

    del calculated_before_spot_usdt
    del calculated_before_spot_busd
    del calculated_before_spot_bnb
    del calculated_before_futures_usdt
    del calculated_before_futures_busd
    del calculated_before_futures_bnb
    del calculated_after_spot_usdt
    del calculated_after_spot_busd
    del calculated_after_spot_bnb
    del calculated_after_futures_usdt
    del calculated_after_futures_busd
    del calculated_after_futures_bnb

    total_usdt = total_usdt - WithdrawCommissions.usdt_commission.value
    total_bnb = total_bnb - WithdrawCommissions.bnb_commission.value

    total_usdt = round(total_usdt, 3)
    total_bnb = round(total_bnb, 4)

    if total_usdt < MinimumWithdrawValues.usdt.value:
        total_usdt = 0.0
    if total_bnb < MinimumWithdrawValues.bnb.value:
        total_bnb = 0.0

    update_profit_values_by_tg_id(user.get("chat_id"), total_usdt, total_bnb)


async def generate_list_of_current_withdraws(update: Update, context: CallbackContext):
    string_to_send = i18n.t("translation.admin.withdraw_list")

    api_location = os.getenv("API_LOCATION")
    if api_location is None:
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.wrong_env_config"))

    # Get calculations from the api
    cashback_results = requests.get(
        api_location +
        "calculations/get_calculation_results_for_all_users/{}?bot_internal_id=" +
        str(Other.bot_id.value)
    )
    if cashback_results.status_code != 200:
        await context.bot.send_message(
            update.effective_chat.id,
            i18n.t("translation.admin.error_during_api_calculations")
        )
        return

    # Calculate with ratios for this user, save to the db
    calculation_results: dict = json.loads(cashback_results.text)

    for user in read_all_users_with_not_null_withdraw_amounts():
        binance_id = str(user.get("binance_id"))
        if binance_id not in calculation_results:
            continue

        sum_from_api = calculation_results.get(binance_id)

        user_name = user.get("real_name")
        user_wallet = user.get("withdraw_wallet")
        user_bid = user.get("binance_id")
        user_withdraw_usdt = user.get("available_to_withdraw_usdt")
        user_withdraw_bnb = user.get("available_to_withdraw_bnb")

        """Before goes for before 30 days of using the bot, 
        after goes for after using bot for 30 days. s_ goes for sum"""
        _before = sum_from_api.get("sum_results_before_user_used_the_bot_for_30_days", {})
        _after = sum_from_api.get("sum_results_after_user_used_the_bot_for_30_days", {})
        _spot = "spot"
        _futures = "futures"
        _before_spot = _before.get(_spot, {})
        _before_futures = _before.get(_futures, {})
        _after_spot = _after.get(_spot, {})
        _after_futures = _after.get(_futures, {})

        before_futures_usdt = _before_futures.get("usdt", 0.0)
        before_futures_busd = _before_futures.get("busd", 0.0)
        after_futures_usdt = _after_futures.get("usdt", 0.0)
        after_futures_busd = _after_futures.get("busd", 0.0)

        del _before
        del _after
        del _spot
        del _futures
        del _before_spot
        del _before_futures
        del _after_spot
        del _after_futures

        sum_usdt_before = sum([before_futures_usdt, before_futures_busd])
        sum_usdt_after = sum([after_futures_usdt, after_futures_busd])
        sum_usdt = formula_for_total_volume_calculation_before_30_days(sum_usdt_before) + \
            formula_for_total_volume_calculation_after_30_days(sum_usdt_after)

        del before_futures_usdt
        del before_futures_busd
        del after_futures_usdt
        del after_futures_busd
        del sum_usdt_before
        del sum_usdt_after

        user_info = f"{user_bid} | {user_name}\n " \
                    f"<code>{user_wallet}</code>\n" \
                    f"<code>{user_withdraw_usdt}</code>USDT | <code>{user_withdraw_bnb}</code>BNB | {sum_usdt}\n\n"
        string_to_send += user_info

    return string_to_send
