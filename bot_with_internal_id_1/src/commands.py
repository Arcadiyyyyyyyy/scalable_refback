import re

import i18n
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from .bot_notifications import notify_about_new_user
from .static.const import QueryCommands, CommandsWithDescriptions, CommandsRelated
from .middleware import main_handler, critical_checks, is_chat_exists
from .db import create_chat, change_chat_language, read_bid, update_registered_user, read_chat


async def start_command(update: Update, context: CallbackContext):
    if not critical_checks(update.effective_chat.id):
        return

    # If user already interacted with the bot before
    if is_chat_exists(update.effective_chat.id):
        # Checks that have to be done every update
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
        await help_command(update, context)
    # If user is not in the database (most certainly sent first ever message to the bot)
    else:
        create_chat(update.effective_chat.id)
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.first_interaction"))


# async def main_menu(update: Update, context: CallbackContext):
#     # Checks that have to be done every update
#     main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
#
#     if not critical_checks(update.effective_chat.id):
#         return
#
#     keyboard = InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton(
#                     i18n.t("translation.support"),
#                     callback_data=QueryCategories.support.value+"*"+QueryCommands.support.value
#                 )
#             ]
#         ]
#     )
#
#     await context.bot.send_message(
#         update.effective_chat.id,
#         i18n.t("translation.menu"),
#         reply_markup=keyboard
#     )


async def help_command(update: Update, context: CallbackContext):
    # Checks that have to be done every update
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

    if not critical_checks(update.effective_chat.id):
        return

    await context.bot.send_message(
        update.effective_chat.id,
        i18n.t("translation.formatted.help").format(
            CommandsWithDescriptions.start.value.get(CommandsRelated.command_name.value),
            CommandsWithDescriptions.support.value.get(CommandsRelated.command_name.value),
            CommandsWithDescriptions.my_data.value.get(CommandsRelated.command_name.value),
            CommandsWithDescriptions.set_data.value.get(CommandsRelated.command_name.value),
        ),
        parse_mode=ParseMode.HTML
    )


async def cancel_command(update: Update, context: CallbackContext):
    # Checks that have to be done every update
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

    if not critical_checks(update.effective_chat.id):
        return

    await context.bot.send_message(update.effective_chat.id, i18n.t("translation.nothing_to_cancel"))


class SetData:
    NAME, BID, WALLET = range(3)
    data = {}

    async def _cancelled(self, update: Update, context: CallbackContext):
        self.data[update.effective_chat.id] = {}
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.wrong_input"))

    async def handle_name(self, update: Update, context: CallbackContext):
        # Checks that have to be done every update
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

        if not critical_checks(update.effective_chat.id):
            return

        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.send_your_full_name"))

        return self.NAME

    async def binance_id_handling(self, update: Update, context: CallbackContext):
        # Checks that have to be done every update
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

        if not critical_checks(update.effective_chat.id):
            return

        if re.fullmatch(r"[a-zA-Z\u0400-\u04FF ]+", update.message.text) is not None:
            self.data[update.effective_chat.id] = {}
            self.data[update.effective_chat.id]["name"] = update.message.text
            await context.bot.send_message(update.effective_chat.id, i18n.t("translation.send_your_bid"))
            return self.BID
        else:
            await self._cancelled(update, context)
            return ConversationHandler.END

    async def wallet_handling(self, update: Update, context: CallbackContext):
        # Checks that have to be done every update
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

        if not critical_checks(update.effective_chat.id):
            return

        if read_bid(int(update.message.text)) is None:
            self.data[update.effective_chat.id]["bid"] = update.message.text
            await context.bot.send_message(
                update.effective_chat.id,
                i18n.t("translation.send_your_wallet"),
                parse_mode=ParseMode.HTML
            )
            return self.WALLET
        else:
            await self._cancelled(update, context)
            return ConversationHandler.END

    async def finish(self, update: Update, context: CallbackContext):
        # Checks that have to be done every update
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

        if not critical_checks(update.effective_chat.id):
            self.data[update.effective_chat.id] = {}
            return

        if re.fullmatch(r"T[a-zA-Z0-9]{33}", update.message.text) is not None:
            self.data[update.effective_chat.id]["wallet"] = update.message.text
            await context.bot.send_message(
                update.effective_chat.id,
                i18n.t("translation.formatted.successfully_registered").format(
                    CommandsWithDescriptions.my_data.value.get(CommandsRelated.command_name.value)
                )
            )
            update_registered_user(
                update.effective_chat.id,
                self.data[update.effective_chat.id].get("name"),
                int(self.data[update.effective_chat.id].get("bid")),
                self.data[update.effective_chat.id].get("wallet"),
            )
            await notify_about_new_user(
                self.data[update.effective_chat.id].get("name"),
                int(self.data[update.effective_chat.id].get("bid")),
                context,
                update.effective_user.username
            )
            self.data[update.effective_chat.id] = {}
            return ConversationHandler.END
        else:
            await self._cancelled(update, context)
            return ConversationHandler.END

    async def cancel(self, update: Update, context: CallbackContext):
        # Checks that have to be done every update
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

        if not critical_checks(update.effective_chat.id):
            return

        self.data[update.effective_chat.id] = {}
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.cancelled"))
        return ConversationHandler.END


async def my_data_command(update: Update, context: CallbackContext):
    # Checks that have to be done every update
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

    if not critical_checks(update.effective_chat.id):
        return

    user = read_chat(update.effective_chat.id)
    name = user.get("real_name")
    bid = user.get("binance_id")
    wallet = user.get("withdraw_wallet")

    if name is not None and bid is not None and wallet is not None:
        await context.bot.send_message(
            update.effective_chat.id,
            i18n.t("translation.formatted.my_data").format(
                name,
                bid,
                wallet
            )
        )
    else:
        await context.bot.send_message(
            update.effective_chat.id,
            i18n.t("translation.you_have_not_registered_yet")
        )


async def local_query_handler(update: Update, context: CallbackContext):
    query = update.callback_query.data.split("*")[1:]
    header_query = query[0]

    if header_query == QueryCommands.lang_code_handle.value:
        change_chat_language(update.effective_chat.id, query[1])
        await update.callback_query.answer()
        await context.bot.delete_message(update.effective_chat.id, update.effective_message.id)
        await help_command(update, context)  # await main_menu(update, context)

    elif header_query == QueryCommands.menu.value:
        await update.callback_query.answer()
        await context.bot.delete_message(update.effective_chat.id, update.effective_message.id)
        await help_command(update, context)  # await main_menu(update, context)
