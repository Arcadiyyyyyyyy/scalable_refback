import datetime
import logging

import i18n
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from .static.const import AdminLevels, QueryCategories, QueryCommands, Other
from .middleware import is_admin, is_chat_private, main_handler
from .db import (
    add_message_to_the_ticket,
    create_support_ticket,
    read_all_admins,
    read_chat,
    read_open_tickets,
    read_selected_ticket,
    read_ticket_messages,
    select_support_ticket,
    unselect_all_tickets,
)


class AddMessage:
    update = None
    context = None
    from_type = None
    user_id = None

    async def start(self, update: Update, context: CallbackContext):
        try:
            main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)

            self.update = update
            self.context = context
            self.from_type = (
                "support_agent"
                if is_admin(self.update, AdminLevels.support_level.value)
                else "user"
            )
            self.user_id = update.effective_chat.id

            if read_selected_ticket(self.user_id, self.from_type) is not None:
                await self._process_content()

                message = update.effective_message
                msg_dict = {"from_user": update.message.chat.id}

                if message.media_group_id:
                    jobs = context.job_queue.get_jobs_by_name(
                        str(message.media_group_id)
                    )

                    if jobs:
                        jobs[0].data.append(msg_dict)
                    else:
                        context.job_queue.run_once(
                            callback=send_message_to_interlocutor,
                            when=2,
                            data=[msg_dict],
                            name=str(message.media_group_id),
                        )
                else:
                    context.job_queue.run_once(
                        callback=send_message_to_interlocutor,
                        when=0,
                        data=[msg_dict],
                        name=str(message.message_id),
                    )
            else:
                await update.message.reply_text(
                    i18n.t("translation.unknown_text_no_tickets_selected")
                )
        except Exception as e:
            await exception_handler(context, e, update)

    async def _process_content(self):
        if self.update.message.text is not None:
            await self._process_text()
        elif self.update.message.animation is not None:
            await self._process_animation()
        elif self.update.message.video is not None:
            await self._process_video()
        elif self.update.message.document is not None:
            await self._process_document()
        elif self.update.message.voice is not None:
            await self._process_voice()
        elif self.update.message.video_note is not None:
            await self._process_video_note()
        elif self.update.message.audio is not None:
            await self._process_audio()
        elif self.update.message.photo is not None and self.update.message.photo:
            await self._process_photo()
        elif self.update.message.sticker is not None:
            await self._process_sticker()
        else:
            await self.update.message.reply_text(
                i18n.t("translation.we_dont_support_this_type_of_message")
            )

    async def _format_message(self, content, message_type: str):
        final = {
            "from": self.from_type,
            "content": content,
            "message_type": message_type,
            "is_message_type": {
                "is_media_group": True
                if self.update.message.media_group_id is not None
                else False,
                "is_reply": True
                if self.update.message.reply_to_message is not None
                else False,
            },
            "message_id": self.update.message.message_id,
            "chat_id": self.update.message.chat.id,
            "date": datetime.datetime.utcnow(),
        }

        if final.get("is_message_type", {}).get("is_media_group") is True:
            final["media_group_id"] = self.update.message.media_group_id
        if final.get("is_message_type", {}).get("is_reply") is True:
            final[
                "reply_to_message_id"
            ] = self.update.message.reply_to_message.message_id

        return final

    async def _process_text(self):
        add_message_to_the_ticket(
            await self._format_message(self.update.message.text, "text"),
            self.user_id,
            self.from_type,
        )

    async def _process_photo(self):
        content = {
            "object_tg_id": self.update.message.photo[0]["file_id"],
        }

        if self.update.message.caption is not None:
            content["caption"] = self.update.message.caption

        add_message_to_the_ticket(
            await self._format_message(content, "photo"), self.user_id, self.from_type
        )

    async def _process_video(self):
        content = {"object_tg_id": self.update.message.video["file_id"]}

        if self.update.message.caption is not None:
            content["caption"] = self.update.message.caption

        add_message_to_the_ticket(
            await self._format_message(content, "video"), self.user_id, self.from_type
        )

    async def _process_document(self):
        content = {"object_tg_id": self.update.message.document["file_id"]}

        if self.update.message.caption is not None:
            content["caption"] = self.update.message.caption

        add_message_to_the_ticket(
            await self._format_message(content, "document"), self.user_id, self.from_type
        )

    async def _process_audio(self):
        content = {"object_tg_id": self.update.message.audio["file_id"]}

        if self.update.message.caption is not None:
            content["caption"] = self.update.message.caption

        add_message_to_the_ticket(
            await self._format_message(content, "audio"), self.user_id, self.from_type
        )

    async def _process_voice(self):
        add_message_to_the_ticket(
            await self._format_message(
                {"object_tg_id": self.update.message.voice["file_id"]}, "voice"
            ),
            self.user_id,
            self.from_type,
        )

    async def _process_animation(self):
        content = {"object_tg_id": self.update.message.document["file_id"]}

        if self.update.message.caption is not None:
            content["caption"] = self.update.message.caption

        add_message_to_the_ticket(
            await self._format_message(content, "animation"), self.user_id, self.from_type
        )

    async def _process_sticker(self):
        add_message_to_the_ticket(
            await self._format_message(
                {"object_tg_id": self.update.message.sticker["file_id"]}, "sticker"
            ),
            self.user_id,
            self.from_type,
        )

    async def _process_video_note(self):
        add_message_to_the_ticket(
            await self._format_message(
                {"object_tg_id": self.update.message.video_note["file_id"]},
                "video_note",
            ),
            self.user_id,
            self.from_type,
        )


async def send_one_message_from_saved(
    context: CallbackContext,
    message: dict | list[dict],
    to_user_id: int,
    without_caption: bool = False,
):
    if type(message) == list and len(message) >= 1:
        media = []
        docs = []

        for msg in message:
            media_str = msg.get("content", {}).get("object_tg_id")
            if without_caption is False:
                standard_caption = "From {:s}\n\n".format(msg.get("from"))
            else:
                standard_caption = ""

            caption_from_who_plus_message_caption = standard_caption + msg.get(
                "content", {}
            ).get("caption", "")
            message_caption = msg.get("content", {}).get("caption", "")

            if msg.get("message_type") == "document":
                if not docs:
                    docs.append(
                        InputMediaDocument(
                            media_str, caption=caption_from_who_plus_message_caption
                        )
                    )
                else:
                    docs.append(InputMediaDocument(media_str, caption=message_caption))

            elif msg.get("message_type") == "audio":
                if not docs:
                    docs.append(
                        InputMediaAudio(
                            media_str, caption=caption_from_who_plus_message_caption
                        )
                    )
                else:
                    docs.append(InputMediaAudio(media_str, caption=message_caption))

            elif msg.get("message_type") == "photo":
                if not media:
                    media.append(
                        InputMediaPhoto(
                            media_str, caption=caption_from_who_plus_message_caption
                        )
                    )
                else:
                    media.append(InputMediaPhoto(media_str, caption=message_caption))

            elif msg.get("message_type") == "video":
                if not media:
                    media.append(
                        InputMediaVideo(
                            media_str, caption=caption_from_who_plus_message_caption
                        )
                    )
                else:
                    media.append(InputMediaVideo(media_str, caption=message_caption))

        if len(media) >= 1:
            await context.bot.send_media_group(to_user_id, media=media)

        elif len(docs) >= 1:
            await context.bot.send_media_group(to_user_id, media=docs)

        return

    else:
        if without_caption is False:
            standard_caption = "From: {:s}\n\n".format(message.get("from"))
        else:
            standard_caption = ""

        if message.get("message_type") == "text":
            await context.bot.send_message(
                to_user_id,
                standard_caption.format(message.get("from"))
                + message.get("content", ""),
            )

        elif message.get("message_type") == "photo":
            await context.bot.send_photo(
                to_user_id,
                message.get("content", {}).get("object_tg_id"),
                caption=standard_caption
                + message.get("content", {}).get("caption", ""),
            )

        elif message.get("message_type") == "video":
            await context.bot.send_video(
                to_user_id,
                message.get("content", {}).get("object_tg_id"),
                caption=standard_caption
                + message.get("content", {}).get("caption", ""),
            )

        elif message.get("message_type") == "document":
            await context.bot.send_document(
                to_user_id,
                message.get("content", {}).get("object_tg_id"),
                caption=standard_caption
                + message.get("content", {}).get("caption", ""),
            )

        elif message.get("message_type") == "voice":
            await context.bot.send_voice(
                to_user_id, message.get("content", {}).get("object_tg_id")
            )

        elif message.get("message_type") == "audio":
            await context.bot.send_audio(
                to_user_id,
                message.get("content", {}).get("object_tg_id"),
                caption=standard_caption
                + message.get("content", {}).get("caption", ""),
            )

        elif message.get("message_type") == "animation":
            await context.bot.send_animation(
                to_user_id,
                message.get("content", {}).get("object_tg_id"),
                caption=standard_caption
                + message.get("content", {}).get("caption", ""),
            )

        elif message.get("message_type") == "sticker":
            await context.bot.send_sticker(
                to_user_id, message.get("content", {}).get("object_tg_id")
            )

        elif message.get("message_type") == "video_note":
            await context.bot.send_video_note(
                to_user_id, message.get("content", {}).get("object_tg_id")
            )


async def send_all_messages_from_saved(update: Update, context: CallbackContext):
    try:
        from_who = (
            "support_agent"
            if is_admin(update, AdminLevels.support_level.value)
            else "user"
        )

        ticket = read_selected_ticket(update.effective_chat.id, from_who)
        media_group_messages = []
        to_user = ticket.get(
            "support_agent"
            if is_admin(update, AdminLevels.support_level.value)
            else "chat_id"
        )

        def send_media_group():
            send_one_message_from_saved(context, media_group_messages, to_user)

        try:
            for message in read_ticket_messages(update.effective_chat.id, from_who):
                if message.get("is_message_type", {}).get("is_media_group") is True:
                    if len(media_group_messages) == 0:
                        media_group_messages.append(message)
                    else:
                        if message.get("media_group_id") == media_group_messages[
                            -1
                        ].get("media_group_id"):
                            media_group_messages.append(message)
                        else:
                            send_media_group()
                            media_group_messages = [message]

                else:
                    if len(media_group_messages) > 0:
                        send_media_group()
                        media_group_messages = []

                    await send_one_message_from_saved(context, message, to_user)

        except IndexError:
            if len(media_group_messages) > 0:
                send_media_group()
                media_group_messages = []
    except Exception as e:
        await exception_handler(context, e, update)


async def send_message_to_interlocutor(context: CallbackContext):
    try:
        from_user = context.job.data[0].get("from_user")
        is_user_admin = is_admin(from_user, AdminLevels.support_level.value)
        from_who = "support_agent" if is_user_admin else "user"

        ticket = read_selected_ticket(from_user, from_who)
        to_user = ticket.get("chat_id" if is_user_admin else "support_agent")
        lang = read_chat(to_user).get("language")

        if ticket.get("is_selected_by_user") is not True:
            await context.bot.send_message(
                to_user,
                i18n.t("translation.formatted.you_have_new_unread_messages", locale=lang).format(
                    ticket.get("heading")
                )
                + "\n\n"
                + i18n.t("translation.please_click_the_button_to_answer", locale=lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                i18n.t("translation.select", locale=lang),
                                callback_data=QueryCategories.support.value
                                + "*"
                                + QueryCommands.my_open_tickets.value
                                + "*"
                                + str(ticket.get("_id")),
                            )
                        ]
                    ]
                ),
            )
        elif ticket.get("selected_by_support") is None:
            await context.bot.send_message(
                to_user,
                i18n.t("translation.formatted.you_have_new_unread_messages", locale=lang).format(
                    ticket.get("heading")
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                i18n.t("translation.select", locale=lang),
                                callback_data=QueryCategories.admin.value
                                + "*"
                                + QueryCommands.ticket_select.value
                                + "*"
                                + str(ticket.get("_id")),
                            )
                        ]
                    ]
                ),
            )
            return

        # If media group
        message = read_ticket_messages(from_user, from_who, reverse=True)
        current_message = message.next()

        if current_message.get("is_message_type", {}).get("is_media_group") is True:
            messages = []
            media_group_id = current_message.get(
                "media_group_id"
            )  # Target media group id

            while (
                current_message.get("is_message_type", {}).get("is_media_group") is True
                and current_message.get("media_group_id") == media_group_id
            ):
                messages.append(current_message)
                current_message = message.next()

            await send_one_message_from_saved(
                context, messages[::-1], to_user, True if is_user_admin else False
            )

        # If not media group
        else:
            await send_one_message_from_saved(
                context, current_message, to_user, True if is_user_admin else False
            )
    except Exception as e:
        await exception_handler(context, e)


async def exception_handler(context, e, update=None):
    if str(e) == "Forbidden: bot was blocked by the user":
        await context.bot.send_message(
            context.job.data[0].get("from_user")
            if update is None
            else update.effective_chat.id,
            i18n.t("translation.interlocutor_have_blocked_the_bot"),
            parse_mode=ParseMode.MARKDOWN,
        )

    else:
        await context.bot.send_message(
            context.job.data[0].get("from_user")
            if update is None
            else update.effective_chat.id,
            i18n.t("translation.formatted.something_went_wrong_please_notify").format(Other.manual_support.value),
            parse_mode=ParseMode.MARKDOWN,
        )
        logging.error(e)


async def send_support_keyboard(update: Update, context: CallbackContext):
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
    await context.bot.send_message(
        update.effective_chat.id,
        i18n.t("translation.choose"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_support_keyboard(),
    )


def create_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    i18n.t("translation.open_new_ticket"),
                    callback_data=QueryCategories.new_ticket.value,
                )
            ],
            [
                InlineKeyboardButton(
                    i18n.t("translation.my_open_tickets"),
                    callback_data=QueryCategories.support.value
                    + "*"
                    + QueryCommands.my_open_tickets.value,
                )
            ],
            [
                InlineKeyboardButton(
                    i18n.t("translation.get_support_help"),
                    callback_data=QueryCategories.support.value
                    + "*"
                    + QueryCommands.support_help.value,
                )
            ],
            [
                InlineKeyboardButton(
                    i18n.t("translation.back"),
                    callback_data=QueryCategories.commands.value
                    + "*"
                    + QueryCommands.menu.value,
                ),
            ],
        ]
    )


def create_my_open_tickets_keyboard(
    update: Update, _: CallbackContext
) -> InlineKeyboardMarkup:
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
    tickets = [ticket for ticket in read_open_tickets(update.effective_chat.id)]

    if tickets:
        keyboard = [
            [
                InlineKeyboardButton(
                    x.get("heading"),
                    callback_data=QueryCategories.support.value
                    + "*"
                    + QueryCommands.my_open_tickets.value
                    + "*"
                    + str(x.get("_id")),
                )
            ]
            for x in tickets
        ]
        keyboard.append(
            [
                InlineKeyboardButton(
                    i18n.t("translation.back"),
                    callback_data=QueryCategories.support.value
                    + "*"
                    + QueryCommands.support.value,
                ),
            ]
        )
        return InlineKeyboardMarkup(keyboard)
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    i18n.t("translation.back"),
                    callback_data=QueryCategories.support.value
                    + "*" + QueryCommands.support.value,
                ),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


class NewTicket:
    HEADING = range(1)
    user_data = {}

    async def start_handler(self, update: Update, context: CallbackContext):
        if is_chat_private(update, context):
            main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
            await update.callback_query.answer()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=i18n.t("translation.ticket_creation_process_start"),
            )
            return self.HEADING
        else:
            return ConversationHandler.END

    async def finish_handler(self, update: Update, context: CallbackContext):
        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
        self.user_data[self.HEADING] = update.message.text

        await self._create_ticket(update, context)

        return ConversationHandler.END

    async def cancel_handler(self, update: Update, context: CallbackContext):
        def end_message(key: str):
            context.bot.send_message(chat_id=update.effective_chat.id, text=i18n.t(key))

        main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
        self.user_data = {}

        if update.callback_query is not None:
            end_message("translation.ticket_creation_process_is_button")
            await update.callback_query.answer()
        elif update.message.text == "/cancel":
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=i18n.t("translation.cancelled")
            )
        elif update.message.text != "/cancel":
            end_message("translation.ticket_creation_process_is_cancelled")
        else:
            end_message("translation.cancelled")

        return ConversationHandler.END

    async def _create_ticket(self, update: Update, context: CallbackContext):
        ticket = create_support_ticket(
            update.effective_chat.id,
            self.user_data.get(self.HEADING, "None"),
        )

        select_support_ticket(ticket.inserted_id, update.effective_chat.id, "user")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=i18n.t("translation.your_ticket_was_successfully_created"),
        )

        await notify_admins_about_new_ticket(context, ticket.inserted_id)


async def exit_command(update: Update, _: CallbackContext):
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
    unselect_results = unselect_all_tickets(update.effective_chat.id, "user")

    if unselect_results.modified_count >= 1:
        await update.message.reply_text(i18n.t("translation.success"))
    else:
        await update.message.reply_text(i18n.t("translation.nothing_happened"))


async def notify_admins_about_new_ticket(context: CallbackContext, ticket_id):
    for admin in read_all_admins(AdminLevels.support_level.value):
        await context.bot.send_message(
            chat_id=admin.get("chat_id"),
            text=i18n.t(
                "translation.new_ticket_was_opened", locale=admin.get("language", "en")
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            i18n.t(
                                "translation.select", locale=admin.get("language", "en")
                            ),
                            callback_data=QueryCategories.admin.value
                            + "*"
                            + QueryCommands.ticket.value
                            + "*"
                            + str(ticket_id),
                        )
                    ]
                ]
            ),
        )


async def query_handler_support(update: Update, context: CallbackContext):
    main_handler(update.effective_chat.id, update.effective_user.first_name, update.effective_user.username)
    if not is_chat_private(update, context):
        return

    query_with_id = update.callback_query.data.split("*")[1:]
    query = query_with_id[0]

    if query == QueryCommands.support.value:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            text=i18n.t("translation.choose"),
            reply_markup=create_support_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await update.callback_query.answer()

    elif query == QueryCommands.support_help.value:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            text=i18n.t("translation.support_help"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            i18n.t("translation.back"),
                            callback_data=QueryCategories.support.value
                            + "*"
                            + QueryCommands.support.value,
                        ),
                    ]
                ]
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        await update.callback_query.answer()

    elif (
        len(query_with_id) == 2 and query_with_id[0] == QueryCommands.my_open_tickets.value
    ):
        await update.callback_query.answer(
            i18n.t("translation.success")
            if select_support_ticket(
                query_with_id[1], update.effective_chat.id, "user"
            ).modified_count
            >= 1
            else i18n.t("translation.nothing_found")
        )

    elif query == QueryCommands.my_open_tickets.value:
        keyboard = create_my_open_tickets_keyboard(update, context)
        if keyboard:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id,
                text=i18n.t("translation.your_open_tickets"),
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
        await update.callback_query.answer()
