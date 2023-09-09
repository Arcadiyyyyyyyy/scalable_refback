import i18n
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from .db import read_chat, read_all_admins
from .static.const import MinimumWithdrawValues


async def notify_about_increased_level(user_tg_id, context: CallbackContext):
    user = read_chat(user_tg_id)
    await context.bot.send_message(
        user_tg_id,
        i18n.t("translation.level_increased", locale=user.get("language", "ru"))
    )


async def notify_about_decreased_level(user_tg_id, context: CallbackContext):
    user = read_chat(user_tg_id)
    await context.bot.send_message(
        user_tg_id,
        i18n.t("translation.level_decreased", locale=user.get("language", "ru"))
    )


async def notify_about_new_payoff(user_tg_id, context: CallbackContext):
    user = read_chat(user_tg_id)
    available_to_withdraw_usdt = user.get("available_to_withdraw_usdt")
    available_to_withdraw_bnb = user.get("available_to_withdraw_bnb")

    usdt_min = MinimumWithdrawValues.usdt.value
    bnb_min = MinimumWithdrawValues.bnb.value

    if available_to_withdraw_usdt > usdt_min or available_to_withdraw_bnb > bnb_min:
        if available_to_withdraw_usdt > usdt_min and available_to_withdraw_bnb > bnb_min:
            text = i18n.t("translation.formatted.you_got_new_payoff")\
                .format(f"{available_to_withdraw_usdt}USDT {available_to_withdraw_bnb}BNB")
        elif available_to_withdraw_usdt > usdt_min:
            text = i18n.t("translation.formatted.you_got_new_payoff")\
                .format(f"{available_to_withdraw_usdt}USDT")
        elif available_to_withdraw_bnb > bnb_min:
            text = i18n.t("translation.formatted.you_got_new_payoff")\
                .format(f"{available_to_withdraw_bnb}BNB")
        else:
            text = i18n.t("translation.error")
        await context.bot.send_message(
            user_tg_id,
            text
        )


async def notify_about_new_user(name, b_id, context: CallbackContext, username=""):
    if username is None:
        username = ""

    for admin in read_all_admins(1):
        try:
            await context.bot.send_message(
                admin.get("chat_id"),
                "<b>Новый пользователь!</b>\n{:s}\n@{:s}\n{:}".format(name, username, b_id) if username != ""
                else "<b>New user!</b>\n{:s}\n{:}".format(name, b_id),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(e)
