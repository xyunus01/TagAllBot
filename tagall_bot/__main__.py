from typing import Generator
import requests
from ptbcontrib.reply_to_message_filter import ReplyToMessageFilter
from ptbcontrib.roles import RolesHandler
from telegram import Chat, Message, Update, User
from telegram.constants import CHAT_PRIVATE, PARSEMODE_MARKDOWN
from telegram.ext import CallbackContext, Filters, Job, JobQueue, PrefixHandler
from telegram.utils.helpers import mention_markdown

from tagall_bot import (
    ADMINS,5622660844
    API_URL,
    DISPATCHER,
    DND_USERS,
    LOGGER,5622660844
    PORT,
    SUDO_USERS,
    TAG_USERS,5622660844
    TOKEN,6256855944:AAEvfoexkpJ_Y0tPkwdEP2JYW1uza-SSudQ
    UPDATER,
    URL,
    WEBHOOK,
)
from tagall_bot.decorators import command_handler
from tagall_bot.error_handler import error_callback, list_errors
from tagall_bot.sql.roles import (
    add_sudo,
    add_tag,
    is_tag_user,
    remove_sudo,
    remove_tag,
)
from tagall_bot.texts import BAD_TEXT, HELP_TEXT, START_TEXT


@command_handler("start", "!")
def start(update: Update, _: CallbackContext) -> None:
    """The start command callback function"""
    if not isinstance(update.effective_message, Message):
        return
    update.effective_message.reply_text(
        text=START_TEXT,
        parse_mode=PARSEMODE_MARKDOWN,
    )


@command_handler("help", "!")
def help_callback(update: Update, _: CallbackContext) -> None:
    """The help command callback function"""
    if not isinstance(update.effective_message, Message):
        return
    update.effective_message.reply_text(
        text=HELP_TEXT,
        parse_mode=PARSEMODE_MARKDOWN,
    )


def send_tag(context: CallbackContext) -> None:
    """The send tag job callback function"""
    if not isinstance(context.job, Job):
        return
    context.bot.send_message(
        text=", ".join(context.job.context[2]),
        chat_id=context.job.context[0],
        reply_to_message_id=context.job.context[1],
        parse_mode=PARSEMODE_MARKDOWN,
    )


def mention_list(chat_id: int):
    """The function to get particiapant's ID and first name from chat ID.
    Uses https://github.com/infinity-plus/chatidToMembersAPI.
    Args:
        - chat_id: int -> chat_id of the chat
    Returns:
        - list[str] -> If the API call was successful.
        - [] if the API call was not successful.
    """
    r = requests.get(url=f"{API_URL}/get", params={"chat_id": chat_id})
    users = r.json() if r.status_code == 200 else {}
    return [
        mention_markdown(user_id, user_name)
        for user_id, user_name in users.items()
        if user_id not in DND_USERS
    ]


def split_list(
    array: list[str],
    chunk_size: int,
) -> Generator[list[str], None, None]:
    """
    Splits a given list evenly into chunk_size.
    https://stackoverflow.com/a/312464/9664447
    Args:
        - array: list[str] -> The list to split.
        - chunk_size: int -> The size of the chunks.
    """
    for i in range(0, len(array), chunk_size):
        yield array[i : i + chunk_size]  # noqa


def schedule_job(
    context: CallbackContext,
    chat_id: int,
    message_id: int,
    tag: list[str],
    delay: int,
):
    """The job scheduler function.
    Args:
        - context: CallbackContext -> The context of the callback.
        - chat_id: int -> The chat ID.
        - message_id: int -> The message ID.
        - tag: list[str] -> The list of tags.
        - delay: int -> The delay in seconds.
    """
    if not isinstance(context.job_queue, JobQueue):
        return
    context.job_queue.run_once(
        callback=send_tag,
        when=3 * delay,
        context=(chat_id, message_id, tag),
    )


@command_handler(
    commands=["tag", "everyone"],
    prefix=["!", "@"],
    filters=ReplyToMessageFilter(Filters.chat_type.groups),
    run_async=True,
    roles=TAG_USERS,
)
def tag_all(update: Update, context: CallbackContext) -> None:
    """The tag all command callback function"""
    if not isinstance(update.effective_message, Message):
        return
    user = update.effective_message.from_user
    chat = update.effective_message.chat
    if user.id in TAG_USERS.chat_ids and not is_tag_user(user.id, chat.id):
        update.effective_message.reply_text(
            text=BAD_TEXT[1],
            parse_mode=PARSEMODE_MARKDOWN,
        )
        return
    message_id = update.effective_message.reply_to_message.message_id
    tags = mention_list(chat.id)
    for i, tag in enumerate(split_list(list(tags), 5)):
        schedule_job(context, chat.id, message_id, tag, i)


@command_handler(
    commands=["tag", "everyone"],
    prefix=["!", "@"],
    run_async=True,
)
def bad_tag(update: Update, _: CallbackContext) -> None:
    """The callback function to handle improper use of tag all command"""
    if not isinstance(update.effective_message, Message) or not isinstance(
        update.effective_chat, Chat
    ):
        return
    if update.effective_chat.type == CHAT_PRIVATE:
        update.effective_message.reply_text(
            text=BAD_TEXT[0],
            parse_mode=PARSEMODE_MARKDOWN,
        )
    elif update.effective_message.reply_to_message is None:
        update.effective_message.reply_text(
            text="Please reply to a message to tag all users of the chat.",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=BAD_TEXT[1],
            parse_mode=PARSEMODE_MARKDOWN,
        )


@command_handler(
    commands="grant",
    prefix="!",
    filters=ReplyToMessageFilter(Filters.chat_type.groups),
    run_async=True,
    roles=SUDO_USERS,
)
def add_tag_user(update: Update, _: CallbackContext):
    """The function to add a user to 'Tag Users' role.
    Callback function of grant command.
    """
    if not isinstance(update.effective_message, Message) or not isinstance(
        update.effective_chat, Chat
    ):
        return
    user: User = update.effective_message.reply_to_message.from_user
    if add_tag(
        user.id,
        update.effective_chat.id,
    ):
        TAG_USERS.add_member(user.id)
        update.effective_message.reply_text(
            text=f"Granted *tag* power to *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=f"Couldn't grant tag power to add *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )


@command_handler(
    commands="grant_su",
    prefix="!",
    filters=ReplyToMessageFilter(Filters.chat_type.groups),
    run_async=True,
    roles=ADMINS,
)
def add_sudo_user(update: Update, _: CallbackContext):
    """The function to add a user to 'Sudo Users' role.
    Callback function of grant_su command.
    """
    if not isinstance(update.effective_message, Message):
        return
    user: User = update.effective_message.reply_to_message.from_user
    if add_sudo(user.id):
        SUDO_USERS.add_member(user.id)
        update.effective_message.reply_text(
            text=f"Granted *superuser* power to *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=f"Couldn't grant superuser power to *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )


@command_handler(
    commands=["grant", "grant_su"],
    prefix="!",
    run_async=True,
)
def bad_add(update: Update, _: CallbackContext) -> None:
    """The callback function to handle improper use of grant command"""
    if not isinstance(update.effective_message, Message) or not isinstance(
        update.effective_chat, Chat
    ):
        return
    if update.effective_chat.type == CHAT_PRIVATE:
        update.effective_message.reply_text(
            text=BAD_TEXT[0],
        )
    elif update.effective_message.reply_to_message is None:
        update.effective_message.reply_text(
            text="Please reply to a user to grant power.",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=BAD_TEXT[1],
            parse_mode=PARSEMODE_MARKDOWN,
        )


@command_handler(
    commands="revoke",
    prefix="!",
    filters=ReplyToMessageFilter(Filters.chat_type.groups),
    run_async=True,
    roles=SUDO_USERS,
)
def remove_tag_user(update: Update, _: CallbackContext):
    """The function to remove a user from 'Tag Users' role.
    Callback function of revoke command.
    """
    if not isinstance(update.effective_message, Message):
        return
    user: User = update.effective_message.reply_to_message.from_user
    if remove_tag(
        user.id,
        update.effective_message.chat.id,
    ):
        TAG_USERS.kick_member(user.id)
        update.effective_message.reply_text(
            text=f"Revoked *tag* power from *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=f"Couldn't revoked tag power from add *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )


@command_handler(
    commands="revoke_su",
    prefix="!",
    filters=ReplyToMessageFilter(Filters.chat_type.groups),
    run_async=True,
    roles=ADMINS,
)
def remove_sudo_user(update: Update, _: CallbackContext):
    """The function to remove a user from 'Sudo Users' role.
    Callback function of revoke_su command.
    """
    if not isinstance(update.effective_message, Message):
        return
    user: User = update.effective_message.reply_to_message.from_user
    if remove_sudo(user.id):
        SUDO_USERS.kick_member(user.id)
        update.effective_message.reply_text(
            text=f"Revoked *superuser* power from *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=f"Couldn't revoke superuser power for *{user.full_name}*",
            parse_mode=PARSEMODE_MARKDOWN,
        )


@command_handler(
    commands=["revoke_su", "revoke"],
    prefix="!",
    run_async=True,
)
def bad_remove(update: Update, _: CallbackContext) -> None:
    """The callback function to handle improper use of revoke command"""
    if not isinstance(update.effective_message, Message) or not isinstance(
        update.effective_chat, Chat
    ):
        return
    if update.effective_chat.type == CHAT_PRIVATE:
        update.effective_message.reply_text(
            text=BAD_TEXT[0],
        )
    elif update.effective_message.reply_to_message is None:
        update.effective_message.reply_text(
            text="Please reply to a user to revoke power.",
            parse_mode=PARSEMODE_MARKDOWN,
        )
    else:
        update.effective_message.reply_text(
            text=BAD_TEXT[1],
            parse_mode=PARSEMODE_MARKDOWN,
        )


if __name__ == "__main__":
    LOGGER.info("Starting Tagall Bot...")
    LOGGER.info("Adding Handlers...")
    DISPATCHER.add_error_handler(
        callback=error_callback,  # type: ignore
        run_async=True,
    )
    if WEBHOOK:
        LOGGER.info("Using Webhook...")
        UPDATER.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=URL + TOKEN,
        )
    else:
        LOGGER.info("Using Long Polling...")
        UPDATER.start_polling()
    UPDATER.idle()
