import json
import os
import re

import i18n
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from .bot_notifications import notify_about_new_payoff, notify_about_decreased_level, notify_about_increased_level
from .static.const import AdminLevels, QueryCommands, QueryCategories, Other
from .middleware import is_admin, is_chat_private, main_handler, calculate_cashback_for_user_with_id, \
    generate_list_of_current_withdraws
from .db import (
    assign_ticket_to_support_agent,
    close_support_ticket,
    read_agent_tickets,
    read_all_new_tickets,
    read_chat,
    read_ticket,
    select_support_ticket,
    write_lines_from_csv, read_all_users_with_not_null_withdraw_amounts, increase_level, decrease_level, read_bid
)
from .support import send_all_messages_from_saved


def constant_checks(update: Update, context: CallbackContext):
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
    if not is_admin(update, AdminLevels.support_level.value):
        return
    if not is_chat_private(update, context):
        return

    return True


async def admin_menu(update: Update, context: CallbackContext):
    if not constant_checks(update, context):
        return

    await update.message.reply_text(
        i18n.t("translation.choose"),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        i18n.t("translation.admin.new_calculation"),
                        callback_data=QueryCategories.conversation_handlers.value +
                        QueryCommands.get_link_to_filechanger_or_document.value
                    ),
                ],
                [
                    InlineKeyboardButton(
                        i18n.t("translation.my_open_tickets"),
                        callback_data=QueryCategories.admin.value
                        + "*"
                        + QueryCommands.my_open_tickets.value,
                    ),
                    InlineKeyboardButton(
                        i18n.t("translation.open_new_ticket"),
                        callback_data=QueryCategories.admin.value
                        + "*"
                        + QueryCommands.new_ticket.value,
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.t("translation.admin.notify_all_users_about_payoff"),
                        callback_data=QueryCategories.admin.value + "*" +
                        QueryCommands.confirm_handle.value + "*" +
                        QueryCommands.notify_new_payoff.value
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.t("translation.admin.increase_level"),
                        callback_data=QueryCategories.conversation_handlers.value + QueryCommands.increase_level.value
                    ),
                    InlineKeyboardButton(
                        i18n.t("translation.admin.decrease_level"),
                        callback_data=QueryCategories.conversation_handlers.value + QueryCommands.decrease_level.value
                    ),
                ]
            ]
        ),
    )


async def list_new_tickets(update: Update, context: CallbackContext) -> None:
    """Searches for tickets that are subscribed to tg_user_id of the admin,
    sends them all in separate messages with the inline button to enter"""
    if not constant_checks(update, context):
        return

    is_there_tickets = False

    for ticket in read_all_new_tickets():
        await update.effective_chat.send_message(
            text=ticket.get("heading", "None"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=i18n.t("translation.start"),
                            callback_data=QueryCategories.admin.value
                            + "*"
                            + QueryCommands.ticket.value
                            + "*"
                            + str(ticket.get("_id")),
                        )
                    ]
                ]
            ),
        )
        is_there_tickets = True

    if is_there_tickets:
        return
    else:
        await update.effective_chat.send_message(i18n.t("translation.nothing_found"))


async def list_admins_tickets(update: Update, context: CallbackContext) -> None:
    if not constant_checks(update, context):
        return

    is_there_tickets = False

    for ticket in read_agent_tickets(update.effective_chat.id, False, heading=1, _id=1):
        await update.effective_chat.send_message(
            text=ticket.get("heading", "None"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=i18n.t("translation.select"),
                            callback_data=QueryCategories.admin.value
                            + "*"
                            + QueryCommands.ticket_select.value
                            + "*"
                            + str(ticket.get("_id")),
                        ),
                        InlineKeyboardButton(
                            text=i18n.t("translation.close"),
                            callback_data=QueryCategories.admin.value
                            + "*"
                            + QueryCommands.ticket_close.value
                            + "*"
                            + str(ticket.get("_id")),
                        ),
                    ]
                ]
            ),
        )
        is_there_tickets = True

    if is_there_tickets:
        return
    else:
        await update.effective_chat.send_message(i18n.t("translation.nothing_found"))


def close_ticket(update: Update, context: CallbackContext, ticket_id: str):
    if not constant_checks(update, context):
        return

    amount_of_changed = close_support_ticket(ticket_id).modified_count

    return True if amount_of_changed >= 1 else False


async def notify_about_new_payoff_button(update: Update, context: CallbackContext):
    if not constant_checks(update, context):
        return

    for user in read_all_users_with_not_null_withdraw_amounts():
        chat_id = user.get("chat_id")

        try:
            await notify_about_new_payoff(chat_id, context)
        except Exception:
            await context.bot.send_message(
                update.effective_chat.id,
                i18n.t("translation.admin.failed_to_notify_user").format(
                    user.get("real_name"), user.get("tg_name", " ")
                )
            )


class NewCalculation:
    link = range(1)

    async def get_link_to_filechanger_or_document(self, update: Update, context: CallbackContext):
        if not constant_checks(update, context):
            return

        await update.callback_query.answer()
        await context.bot.send_message(
            update.effective_chat.id,
            i18n.t("translation.send_a_file_or_a_link"),
            disable_web_page_preview=True
        )
        return self.link

    @staticmethod
    async def cancel(update: Update, context: CallbackContext):
        if not constant_checks(update, context):
            return

        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.cancelled"))
        return ConversationHandler.END

    @staticmethod
    async def finish(update: Update, context: CallbackContext):
        async def _exception():
            await context.bot.send_message(
                update.effective_chat.id,
                i18n.t("translation.error")
            )

        if update.message.document is not None or update.message.text is not None:
            if update.message.text is not None:
                if re.fullmatch(r"https://pixeldrain.com/u/[a-zA-Z0-9]{3,12}", update.message.text) is not None:
                    code = str(update.message.text).lstrip("https://pixeldrain.com/u/").split("?")[0]
                    link = "https://pixeldrain.com/api/file/" + str(code) + "?download"
                    get = requests.get(
                        link,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                        }
                    )
                elif re.fullmatch(
                        r"https://filetransfer.io/data-package/[a-zA-Z0-9]{3,12}/download",
                        update.message.text
                ) is not None:
                    get = requests.get(
                        update.message.text,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                        }
                    )
                else:
                    await context.bot.send_message(update.effective_chat.id, i18n.t("translation.admin.wrong_link"))
                    return ConversationHandler.END

                with open("newest.csv", "wb") as f:
                    if get.status_code == 200:
                        f.write(get.content)
                    else:
                        await _exception()

            if update.message.document is not None:
                if update.message.document.file_name[-4:] == ".csv":
                    file = await context.bot.get_file(update.message.document.file_id)
                    await file.download_to_drive("newest.csv")

            await context.bot.send_message(update.message.from_user.id, i18n.t("translation.admin.started_calculation"))

            with open("newest.csv", "r") as f:
                file = f.read()

            api_location = os.getenv("API_LOCATION")
            if api_location is None:
                await context.bot.send_message(update.effective_chat.id, i18n.t("translation.wrong_env_config"))

            # Prune api db
            prune_result = requests.post(
                api_location +
                "calculations/prune_db_documents_with_internal_id/{}?bot_internal_id=" +
                str(Other.bot_id.value)
            )
            if prune_result.status_code != 200:
                await context.bot.send_message(
                    update.effective_chat.id,
                    i18n.t("translation.admin.error_during_db_prune")
                )
                return ConversationHandler.END

            # Write data to the db
            write_lines_from_csv(Other.bot_id.value, file)

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
                return ConversationHandler.END

            # Calculate with ratios for this user, save to the db
            calculation_results: dict = json.loads(cashback_results.text)
            for bid in calculation_results:
                calculate_cashback_for_user_with_id(
                    calculation_results.get(bid),
                    int(bid)
                )

            await context.bot.send_message(update.effective_chat.id, i18n.t("translation.admin.calculation_successful"))

            await context.bot.send_message(
                update.effective_chat.id,
                await generate_list_of_current_withdraws(update, context),
                ParseMode.HTML
            )

            return ConversationHandler.END
        else:
            await context.bot.send_message(update.effective_chat.id, i18n.t("translation.admin.unknown_input"))


class IncreaseLevel:
    BINANCE_ID = range(1)

    async def handle_id(self, update: Update, context: CallbackContext):
        await update.callback_query.answer()
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.admin.send_binance_id"))
        return self.BINANCE_ID

    @staticmethod
    async def finish(update: Update, context: CallbackContext):
        if not constant_checks(update, context):
            return

        if re.fullmatch(r"[0-9]+", update.message.text) is not None:
            result = increase_level(int(update.message.text))
            if result is not None and result.modified_count >= 1:
                await context.bot.send_message(update.effective_chat.id, i18n.t("translation.success"))
                await notify_about_increased_level(read_bid(int(update.message.text)).get("chat_id"), context)
            else:
                await context.bot.send_message(
                    update.effective_chat.id,
                    i18n.t("translation.admin.level_wasnt_changed")
                )

        return ConversationHandler.END

    @staticmethod
    async def cancel(update: Update, context: CallbackContext):
        if not constant_checks(update, context):
            return

        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.cancelled"))

        return ConversationHandler.END


class DecreaseLevel:
    BINANCE_ID = range(1)

    async def handle_id(self, update: Update, context: CallbackContext):
        await update.callback_query.answer()
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.admin.send_binance_id"))
        return self.BINANCE_ID

    @staticmethod
    async def finish(update: Update, context: CallbackContext):
        if not constant_checks(update, context):
            return

        if re.fullmatch(r"[0-9]+", update.message.text) is not None:
            result = decrease_level(int(update.message.text))
            if result is not None and result.modified_count >= 1:
                await context.bot.send_message(update.effective_chat.id, i18n.t("translation.success"))
                await notify_about_decreased_level(read_bid(int(update.message.text)).get("chat_id"), context)
            else:
                await context.bot.send_message(
                    update.effective_chat.id,
                    i18n.t("translation.admin.level_wasnt_changed")
                )

        return ConversationHandler.END

    @staticmethod
    async def cancel(update: Update, context: CallbackContext):
        if not constant_checks(update, context):
            return

        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.cancelled"))

        return ConversationHandler.END


async def query_handler_admin(update: Update, context: CallbackContext):
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
    query_with_id = update.callback_query.data.split("*")[1:]
    query = query_with_id[0]

    if query == QueryCommands.admin.value:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            text=i18n.t("translation.choose"),
            reply_markup=await admin_menu(update, context),
            parse_mode=ParseMode.MARKDOWN,
        )

        await update.callback_query.answer()

    elif query == QueryCommands.confirm_handle.value:
        query_for_input = "*".join(query_with_id[1:])

        await context.bot.send_message(
            update.effective_chat.id,
            i18n.t("translation.confirm"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            i18n.t("translation.confirm"),
                            callback_data=QueryCategories.admin.value + "*" + query_for_input
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            i18n.t("translation.cancel"),
                            callback_data=QueryCategories.admin.value + "*" + QueryCommands.delete.value
                        )
                    ]
                ]
            )
        )

        await update.callback_query.answer()

    elif query == QueryCommands.delete.value:
        await update.callback_query.answer()
        await context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id
        )

    elif query == QueryCommands.new_ticket.value:
        await list_new_tickets(update, context)
        await update.callback_query.answer()

    elif query == QueryCommands.notify_new_payoff.value:
        await notify_about_new_payoff_button(update, context)
        await update.callback_query.answer()
        await context.bot.send_message(update.effective_chat.id, i18n.t("translation.success"))

    elif query == QueryCommands.my_open_tickets.value:
        await list_admins_tickets(update, context)
        await update.callback_query.answer()

    elif len(query_with_id) == 2 and query_with_id[0] == QueryCommands.ticket.value:
        if not constant_checks(update, context):
            return
        response = assign_ticket_to_support_agent(
            update.effective_chat.id, query_with_id[1]
        )
        ticket = read_ticket(query_with_id[1])

        select_support_ticket(query_with_id[1], update.effective_chat.id, "support")
        await update.callback_query.answer(
            i18n.t("translation.success")
            if response.modified_count >= 1
            else i18n.t("translation.nothing_found")
        )
        if response.modified_count >= 1:
            await update.callback_query.message.reply_text(
                i18n.t("translation.formatted.you_have_selected_ticket_no").format(
                    query_with_id[1], ticket.get("heading")
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            ticket = read_ticket(query_with_id[1])
            await context.bot.send_message(
                ticket.get("chat_id"),
                i18n.t(
                    "translation.your_ticket_was_opened",
                    locale=read_chat(ticket.get("chat_id")).get("language"),
                ).format(ticket.get("heading")),
                parse_mode=ParseMode.MARKDOWN,
            )

    # If ticket select button is pressed
    elif len(query_with_id) == 2 and query_with_id[0] == QueryCommands.ticket_select.value:
        ticket = read_ticket(query_with_id[1])

        if (
            ticket.get("selected_by_support") is None
            and ticket.get("state") != "closed"
        ):
            select_support_ticket(query_with_id[1], update.effective_chat.id, "support")
            await update.callback_query.message.reply_text(
                i18n.t("translation.formatted.you_have_selected_ticket_no").format(
                    query_with_id[1], ticket.get("heading"), ticket.get("uid")
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            await send_all_messages_from_saved(update, context)
        await update.callback_query.answer()

    # If ticket close button is pressed
    elif len(query_with_id) == 2 and query_with_id[0] == QueryCommands.ticket_close.value:
        await update.effective_chat.send_message(
            i18n.t("translation.please_confirm"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            i18n.t("translation.confirm"),
                            callback_data=QueryCategories.admin.value
                            + "*"
                            + QueryCommands.ticket_close.value
                            + "*"
                            + query_with_id[1]
                            + "*"
                            + "True",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            i18n.t("translation.cancel"),
                            callback_data=QueryCategories.admin.value
                            + "*"
                            + QueryCommands.ticket_close.value
                            + "*"
                            + query_with_id[1]
                            + "*"
                            + "False",
                        )
                    ],
                ]
            ),
        )
        await update.callback_query.answer()

    # If the button pressed in the confirmation menu
    elif len(query_with_id) == 3 and query_with_id[0] == QueryCommands.ticket_close.value:
        if query_with_id[2] == "True":
            if close_ticket(update, context, query_with_id[1]):
                await update.callback_query.answer(i18n.t("translation.success"))

                ticket = read_ticket(query_with_id[1])
                try:
                    await context.bot.send_message(
                        ticket.get("chat_id"),
                        i18n.t(
                            "translation.formatted.the_ticket_was_closed",
                            locale=read_chat(ticket.get("chat_id")).get("language"),
                        ).format(ticket.get("heading")),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass

                await update.effective_message.delete()
            else:
                await update.effective_chat.send_message(
                    i18n.t("translation.nothing_happened")
                )
                await update.callback_query.answer()
        else:
            await update.effective_message.delete()
            await update.callback_query.answer(i18n.t("translation.cancelled"))
