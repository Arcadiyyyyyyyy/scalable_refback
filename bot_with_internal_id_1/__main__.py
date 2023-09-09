from warnings import filterwarnings

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters, ConversationHandler, CallbackContext,
)
from telegram import Update
from telegram.warnings import PTBUserWarning

from src.db import read_selected_ticket
from src.middleware import main_handler, is_admin, generate_command_list
from src import admin, support
from src import commands
from src.static.const import CommandsWithDescriptions, QueryCategories, CommandsRelated, AdminLevels, QueryCommands

from dotenv import load_dotenv
from sys import stderr
import logging
import i18n
import os


# Configure logging
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

logger = logging.getLogger()

try:
    logger.removeHandler(logger.handlers[0])
except IndexError:
    pass

logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(filename)s | Line: %(lineno)d | %(name)s | %(message)s')

stdout_handler = logging.StreamHandler(stderr)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)


# Turn off redundant PTB warnings
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


# set up i18n localization/internationalization
locale_path = os.path.abspath('./locale')

i18n.load_path.append(locale_path)
i18n.set("fallback", "ru")
i18n.set("locale", "ru")


async def callback_query_distributor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global Callback Query distributor.
    It's much easier to handle callbacks in one place, than in 100 different commands"""

    # Checks for mypy
    if update.callback_query is None or update.callback_query.data is None:
        raise Exception("Input error")

    category = update.callback_query.data.split("*")[0]

    if category == QueryCategories.commands.value:
        return await commands.local_query_handler(update, context)
    elif category == QueryCategories.support.value:
        return await support.query_handler_support(update, context)
    elif category == QueryCategories.admin.value:
        return await admin.query_handler_admin(update, context)

    logging.warning("Unknown query category type {:}. Some of your commands will work wrong.".format(category))


async def all_text_handler(update: Update, context: CallbackContext):
    """This function handles all non-conversationHandler related text inputs"""
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

    user_type = (
        "support_agent" if is_admin(update, AdminLevels.support_level.value) else "user"
    )
    ticket = read_selected_ticket(update.effective_chat.id, user_type)

    if update.message is None:
        return

    if update.message.chat.type == "private":
        if update.message.text is not None and update.message.text[0] != "/":
            if ticket is not None:
                await support.AddMessage().start(update, context)
                return
        else:
            if ticket is not None:
                await support.AddMessage().start(update, context)
                return

    if update.message.text is not None:
        await unknown_text(update, context)


async def unknown_text(update: Update, context: CallbackContext):
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

    await context.bot.send_message(
        chat_id=update.message.chat_id, text=i18n.t("translation.unknown_text")
    )


def main() -> None:
    # Get bot token from .env file
    load_dotenv()
    bot_token = os.getenv("TG_BOT_TOKEN")
    command = CommandsRelated.command_name.value

    if bot_token is None:
        logging.critical("TG_BOT token not found. Check .env")
        return

    application = Application.builder().token(bot_token).post_init(generate_command_list).build()

    """Place for ConversationHandlers. Should be registered in the top, 
        because can be called with callback that should be handled with their own handlers"""
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    support.NewTicket().start_handler,
                    pattern=QueryCategories.new_ticket.value,
                )
            ],
            states={
                support.NewTicket().HEADING: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        support.NewTicket().finish_handler,
                    )
                ],
            },
            fallbacks=[
                MessageHandler(filters.COMMAND, support.NewTicket().cancel_handler),
                CallbackQueryHandler(support.NewTicket().cancel_handler),
            ],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    admin.IncreaseLevel().handle_id,
                    pattern=QueryCategories.conversation_handlers.value+QueryCommands.increase_level.value,
                )
            ],
            states={
                admin.IncreaseLevel().BINANCE_ID: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        admin.IncreaseLevel().finish,
                    )
                ],
            },
            fallbacks=[
                MessageHandler(filters.COMMAND, admin.IncreaseLevel().cancel),
                CallbackQueryHandler(admin.IncreaseLevel().cancel),
            ],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    admin.DecreaseLevel().handle_id,
                    pattern=QueryCategories.conversation_handlers.value + QueryCommands.decrease_level.value,
                )
            ],
            states={
                admin.DecreaseLevel().BINANCE_ID: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        admin.DecreaseLevel().finish,
                    )
                ],
            },
            fallbacks=[
                MessageHandler(filters.COMMAND, admin.DecreaseLevel().cancel),
                CallbackQueryHandler(admin.DecreaseLevel().cancel),
            ],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    admin.NewCalculation().get_link_to_filechanger_or_document,
                    pattern=QueryCategories.conversation_handlers.value +
                    QueryCommands.get_link_to_filechanger_or_document.value,
                )
            ],
            states={
                support.NewTicket().HEADING: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        admin.NewCalculation().finish,
                    ),
                    MessageHandler(
                        filters.Document.ALL,
                        admin.NewCalculation().finish
                    )
                ],
            },
            fallbacks=[
                MessageHandler(filters.COMMAND, admin.NewCalculation().cancel),
                CallbackQueryHandler(admin.NewCalculation().cancel),
            ],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    CommandsWithDescriptions.set_data.value.get(command),
                    commands.SetData().handle_name,
                )
            ],
            states={
                commands.SetData().NAME: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        commands.SetData().binance_id_handling,
                    ),
                ],
                commands.SetData().BID: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        commands.SetData().wallet_handling,
                    ),
                ],
                commands.SetData().WALLET: [
                    MessageHandler(
                        filters.TEXT & (~filters.COMMAND),
                        commands.SetData().finish,
                    ),
                ],
            },
            fallbacks=[
                MessageHandler(filters.COMMAND, commands.SetData().cancel),
                CallbackQueryHandler(commands.SetData().cancel),
            ],
        )
    )

    # Place for simple commands
    application.add_handler(
        CommandHandler(
            CommandsWithDescriptions.start.value.get(command),
            commands.start_command
        )
    )
    # application.add_handler(
    #     CommandHandler(
    #         CommandsWithDescriptions.menu.value.get(command),
    #         commands.main_menu
    #     )
    # )
    # application.add_handler(
    #     CommandHandler(
    #         CommandsWithDescriptions.help.value.get(command),
    #         commands.help_command
    #     )
    # )
    application.add_handler(
        CommandHandler(
            CommandsWithDescriptions.cancel.value.get(command),
            commands.cancel_command
        )
    )
    application.add_handler(
        CommandHandler(
            CommandsWithDescriptions.my_data.value.get(command),
            commands.my_data_command
        )
    )
    application.add_handler(
        CommandHandler(
            CommandsWithDescriptions.exit.value.get(command),
            support.exit_command
        )
    )
    application.add_handler(
        CommandHandler(
            CommandsWithDescriptions.support.value.get(command),
            support.send_support_keyboard,
            filters.ChatType.PRIVATE
        )
    )
    application.add_handler(
        CommandHandler("admin", admin.admin_menu)
    )

    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, all_text_handler))

    application.add_handler(CallbackQueryHandler(callback_query_distributor))

    # Run the bot until the admin presses Ctrl-C
    logging.warning("Bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
