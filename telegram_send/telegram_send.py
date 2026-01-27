#!/usr/bin/env python3
# telegram-send - Send messages and files over Telegram from the command-line
# Copyright (C) 2016-2026  Rahiel Kasim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import argparse
import asyncio
import configparser
import re
import sys
from copy import deepcopy
from os import makedirs, remove
from os.path import dirname, exists, expanduser, join
from random import randint
from shutil import which
from typing import NamedTuple
from subprocess import check_output
from warnings import warn

import telegram
from telegram.constants import MessageLimit

from .version import __version__
from .utils import pre_format, split_message, get_config_path, markup

try:
    import readline
except ImportError:
    pass


try:
    from colorama import just_fix_windows_console
    just_fix_windows_console()
except ImportError:
    pass


global_config = "/etc/telegram-send.conf"


def main():
    asyncio.run(run())


async def run():
    parser = argparse.ArgumentParser(description="Send messages and files over Telegram.",
                                     epilog="Homepage: https://github.com/rahiel/telegram-send")
    parser.add_argument("message", help="message(s) to send", nargs="*")
    parser.add_argument("--format", default="text", dest="parse_mode", choices=["text", "markdown", "html"],
                        help="How to format the message(s). Choose from 'text', 'markdown', or 'html'")
    parser.add_argument("--stdin", help="Send text from stdin.", action="store_true")
    parser.add_argument("--pre", help="Send preformatted fixed-width (monospace) text.", action="store_true")
    parser.add_argument("--disable-web-page-preview", help="disable link previews in the message(s)",
                        action="store_true")
    parser.add_argument("--silent", help="send silently, user will receive a notification without sound",
                        action="store_true")
    parser.add_argument("-c", "--configure", help="configure %(prog)s", action="store_true")
    parser.add_argument("--configure-channel", help="configure %(prog)s for a channel", action="store_true")
    parser.add_argument("--configure-group", help="configure %(prog)s for a group", action="store_true")
    parser.add_argument("-f", "--file", help="send file(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-i", "--image", help="send image(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-s", "--sticker", help="send stickers(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--animation", help="send animation(s) (GIF or soundless H.264/MPEG-4 AVC video)",
                        nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--video", help="send video(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--audio", help="send audio(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-l", "--location",
                        help="send location(s) via latitude and longitude (separated by whitespace or a comma)",
                        nargs="+")
    parser.add_argument("--caption", help="caption for image(s)", nargs="+")
    parser.add_argument("--showids", help="show message ids, used to delete messages after they're sent",
                        action="store_true")
    parser.add_argument("-d", "--delete", metavar="id",
                        help="delete sent messages by id (only last 48h), see --showids",
                        nargs="+", type=int)
    parser.add_argument("--config", help="specify configuration file", type=str, dest="conf", action="append")
    parser.add_argument("-g", "--global-config", help="Use the global configuration at /etc/telegram-send.conf",
                        action="store_true")
    parser.add_argument("--file-manager", help="Integrate %(prog)s in the file manager", action="store_true")
    parser.add_argument("--clean", help="Clean %(prog)s configuration files.", action="store_true")
    parser.add_argument("--timeout", help="Set the read timeout for network operations. (in seconds)",
                        type=float, default=30., action="store")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    conf : list[str | None]

    if args.global_config:
        conf = [global_config]
    elif args.conf is None:
        conf = [None]
    else:
        conf = args.conf

    if args.configure:
        return await configure(conf[0], fm_integration=True)
    elif args.configure_channel:
        return await configure(conf[0], channel=True)
    elif args.configure_group:
        return await configure(conf[0], group=True)
    elif args.file_manager:
        if not sys.platform.startswith("win32"):
            return integrate_file_manager()
        else:
            print(markup("File manager integration is unavailable on Windows.", "red"))
            sys.exit(1)
    elif args.clean:
        return clean()

    if args.parse_mode == "markdown":
        # Use the improved MarkdownV2 format by default
        args.parse_mode = telegram.constants.ParseMode.MARKDOWN_V2

    if args.stdin:
        message = sys.stdin.read()
        if len(message) == 0:
            sys.exit(0)
        args.message = [message] + args.message

    try:
        await delete(args.delete, conf=conf[0])
        message_ids = []
        for c in conf:
            message_ids += await send(
                messages=args.message,
                conf=c,
                parse_mode=args.parse_mode,
                pre=args.pre,
                silent=args.silent,
                disable_web_page_preview=args.disable_web_page_preview,
                files=args.file,
                images=args.image,
                stickers=args.sticker,
                animations=args.animation,
                videos=args.video,
                audios=args.audio,
                captions=args.caption,
                locations=args.location,
                timeout=args.timeout
            )
        if args.showids and message_ids:
            smessage_ids = [str(m) for m in message_ids]
            print(f"message_ids {' '.join(smessage_ids)}")
    except ConfigError as e:
        print(markup(str(e), "red"))
        print(f"Please read the docs and configure correctly.")
        sys.exit(1)
    except telegram.error.NetworkError as e:
        if "timed out" in str(e).lower():
            print(markup("Error: Connection timed out", "red"))
            print("Please run with a longer timeout.\n"
                  f"Try with the option: {markup(f'--timeout {args.timeout + 10}', 'bold')}")
            sys.exit(1)
        else:
            raise e


async def send(*,
         messages=None, files=None, images=None, stickers=None, animations=None, videos=None, audios=None,
         captions=None, locations=None, conf=None, parse_mode=None, pre=False, silent=False,
         disable_web_page_preview=False, timeout=30):
    """Send data over Telegram. All arguments are optional.

    Always use this function with explicit keyword arguments. So
    `send(messages=["Hello!"])` instead of `send(["Hello!"])`.

    The `file` type is the [file object][] returned by the `open()` function.
    To send an image/file you open it in binary mode:
    ``` python
    import telegram_send

    with open("image.jpg", "rb") as f:
        telegram_send.send(images=[f])
    ```

    [file object]: https://docs.python.org/3/glossary.html#term-file-object

    # Arguments

    - conf (str): Path of configuration file to use. Will use the default config if not specified.
                   `~` expands to user's home directory.
    - messages (list[str]): The messages to send.
    - parse_mode (str): Specifies formatting of messages, one of `["text", "markdown", "html"]`.
    - pre (bool): Send messages as preformatted fixed width (monospace) text.
    - files (list[file]): The files to send.
    - images (list[file]): The images to send.
    - stickers (list[file]): The stickers to send.
    - animations (list[file]): The animations to send.
    - videos (list[file]): The videos to send.
    - audios (list[file]): The audios to send.
    - captions (list[str]): The captions to send with the images/files/animations/videos or audios.
    - locations (list[str]): The locations to send. Locations are strings containing the latitude and longitude
                             separated by whitespace or a comma.
    - silent (bool): Send silently without sound.
    - disable_web_page_preview (bool): Disables web page previews for all links in the messages.
    - timeout (int|float): The read timeout for network connections in seconds.
    """
    settings = get_config_settings(conf)
    token = settings.token
    chat_id = settings.chat_id
    reply_to_message_id = settings.reply_to_message_id
    bot = telegram.Bot(token)

    # We let the user specify "text" as a parse mode to be more explicit about
    # the lack of formatting applied to the message, but "text" isn't a supported
    # parse_mode in python-telegram-bot. Instead, set the parse_mode to None
    # in this case.
    if parse_mode == "text":
        parse_mode = None

    # collect all message ids sent during the current invocation
    message_ids = []

    kwargs = {
        "chat_id": chat_id,
        "disable_notification": silent,
        "read_timeout": timeout,
        "reply_to_message_id": reply_to_message_id
    }

    if messages:
        async def send_message(message, parse_mode):
            if pre:
                parse_mode = "html"
                message = pre_format(message)
            return await bot.send_message(
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                **kwargs
            )

        for m in messages:
            if len(m) > MessageLimit.MAX_TEXT_LENGTH:
                warn(markup(
                    f"Message longer than MAX_MESSAGE_LENGTH={MessageLimit.MAX_TEXT_LENGTH}, splitting into smaller messages.",
                    "red"))
                ms = split_message(m, MessageLimit.MAX_TEXT_LENGTH)
                for m in ms:
                    message_ids += [(await send_message(m, parse_mode))["message_id"]]
            elif len(m) == 0:
                continue
            else:
                message_ids += [(await send_message(m, parse_mode))["message_id"]]

    def make_captions(items, captions):
        # make captions equal length when not all images/files have captions
        captions += [None] * (len(items) - len(captions))
        return zip(items, captions)

    # kwargs for send methods with caption support
    kwargs_caption = deepcopy(kwargs)
    kwargs_caption["parse_mode"] = parse_mode

    if files:
        if captions:
            for (f, c) in make_captions(files, captions):
                message_ids += [await bot.send_document(document=f, caption=c, **kwargs_caption)]
        else:
            for f in files:
                message_ids += [await bot.send_document(document=f, **kwargs)]

    if images:
        if captions:
            for (i, c) in make_captions(images, captions):
                message_ids += [await bot.send_photo(photo=i, caption=c, **kwargs_caption)]
        else:
            for i in images:
                message_ids += [await bot.send_photo(photo=i, **kwargs)]

    if stickers:
        for i in stickers:
            message_ids += [await bot.send_sticker(sticker=i, **kwargs)]

    if animations:
        if captions:
            for (a, c) in make_captions(animations, captions):
                message_ids += [await bot.send_animation(animation=a, caption=c, **kwargs_caption)]
        else:
            for a in animations:
                message_ids += [await bot.send_animation(animation=a, **kwargs)]

    if videos:
        if captions:
            for (v, c) in make_captions(videos, captions):
                message_ids += [await bot.send_video(video=v, caption=c, supports_streaming=True, **kwargs_caption)]
        else:
            for v in videos:
                message_ids += [await bot.send_video(video=v, supports_streaming=True, **kwargs)]

    if audios:
        if captions:
            for (a, c) in make_captions(audios, captions):
                message_ids += [await bot.send_audio(audio=a, caption=c, **kwargs_caption)]
        else:
            for a in audios:
                message_ids += [await bot.send_audio(audio=a, **kwargs)]

    if locations:
        it = iter(locations)
        for loc in it:
            if "," in loc:
                lat, lon = loc.split(",")
            else:
                lat = loc
                lon = next(it)
            message_ids += [await bot.send_location(latitude=float(lat),
                                                    longitude=float(lon),
                                                    **kwargs)]

    return message_ids


async def delete(message_ids, conf=None, timeout=30):
    """Delete messages that have been sent before over Telegram. Restrictions given by Telegram API apply.

    Note that Telegram restricts this to messages which have been sent during the last 48 hours.
    https://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html#telegram.Bot.delete_message

    # Arguments

    - message_ids (list[str]): The messages ids of all messages to be deleted.
    - conf (str): Path of configuration file to use. Will use the default config if not specified.
                  `~` expands to user's home directory.
    - timeout (int|float): The read timeout for network connections in seconds.
    """
    settings = get_config_settings(conf)
    token = settings.token
    chat_id = settings.chat_id
    bot = telegram.Bot(token)

    if message_ids:
        for m in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=m, read_timeout=timeout)
            except telegram.error.TelegramError as e:
                warn(markup(f"Deleting message with id={m} failed: {e}", "red"))


async def configure(conf=None, channel=False, group=False, fm_integration=False):
    """Guide user to set up the bot, saves configuration at `conf`.

    # Arguments

    - conf (str): Path where to save the configuration file. May contain `~` for
                  user's home.
    - channel (bool, optional): Configure a channel.
    - group (bool, optional): Configure a group.
    - fm_integration (bool, optional): Setup file manager integration.
    """
    conf = expanduser(conf) if conf else get_config_path()
    prompt = "❯ "
    contact_url = "https://telegram.me/"
    root_topic_message = None

    print(f"Talk with the {markup('BotFather', 'cyan')} on Telegram ({contact_url}BotFather), "
          "create a bot and insert the token")
    try:
        token = input(markup(prompt, "magenta")).strip()
    except UnicodeEncodeError:
        # some users can only display ASCII
        prompt = "> "
        token = input(markup(prompt, "magenta")).strip()

    try:
        bot = telegram.Bot(token)
        bot_details = await bot.get_me()
        bot_name = bot_details.username
        assert bot_name is not None
    except Exception as e:
        print(f"Error: {e}")
        print(markup("Something went wrong, please try again.\n", "red"))
        return await configure(conf, channel=channel, group=group, fm_integration=fm_integration)

    print(f"Connected with {markup(bot_name, 'cyan')}.\n")

    if channel:
        print(f"Do you want to send to a {markup('public', 'bold')} or a {markup('private', 'bold')} channel? [pub/priv]")
        channel_type = input(markup(prompt, "magenta")).strip()
        if channel_type.startswith("pub"):
            print(
                "\nEnter your channel's public name or link: "
                "\nExample: @username or https://t.me/username"
            )
            chat_id = input(markup(prompt, "magenta")).strip()
            if "/" in chat_id:
                chat_id = "@" + chat_id.split("/")[-1]
            elif chat_id.startswith("@"):
                pass
            else:
                chat_id = "@" + chat_id
        else:
            print(
                "\nOpen https://web.telegram.org/?legacy=1#/im in your browser, sign in and open your private channel."
                "\nNow copy the URL in the address bar and enter it here:"
                "\nExample: https://web.telegram.org/?legacy=1#/im?p=c1498081025_17886896740758033425"
            )
            url = input(markup(prompt, "magenta")).strip()
            match = re.match(r".+web\.(telegram|tlgr)\.org\/\?legacy=1#\/im\?p=c(?P<chat_id>\d+)_\d+", url)
            if not match:
                print(markup("Invalid URL.", "red"))
                return await configure(conf, channel=channel, group=group, fm_integration=fm_integration)
            chat_id = "-100" + match.group("chat_id")

        authorized = False
        while not authorized:
            try:
                await bot.send_chat_action(chat_id=chat_id, action="typing")
                authorized = True
            except (telegram.error.Forbidden, telegram.error.BadRequest):
                # Telegram returns a BadRequest when a non-admin bot tries to send to a private channel
                input(f"Please add {markup(bot_name, 'cyan')} as administrator to your channel and press Enter")
        print(markup("\nCongratulations! telegram-send can now post to your channel!", "green"))
    else:
        password = "".join([str(randint(0, 9)) for _ in range(5)])
        bot_url = contact_url + bot_name
        fancy_bot_name = markup(bot_name, "cyan")
        if group:
            password = f"/{password}@{bot_name}"
            print(f"Please add {fancy_bot_name} to your group\nand send the following message to the group: "
                  f"{markup(password, 'bold')}\n")
        else:
            print(f"Please add {fancy_bot_name} on Telegram ({bot_url})\nand send it the password: "
                  f"{markup(password, 'bold')}\n")

        update, update_id = None, None

        async def get_user():
            updates = await bot.get_updates(offset=update_id, read_timeout=10)
            for update in updates:
                if update.message:
                    if update.message.text == password:
                        return update, None
            if len(updates) > 0:
                return None, updates[-1].update_id + 1
            else:
                return None, None

        def get_root_topic_message(message: telegram.Message):
            while message.reply_to_message is not None:
                message = message.reply_to_message

            if message.forum_topic_created is not None:
                return message
            return None

        while update is None:
            try:
                update, update_id = await get_user()
            except Exception as e:
                print(f"Error! {e}")

        chat_id = update.message.chat_id
        user = update.message.from_user.username or update.message.from_user.first_name

        if update.message.chat.is_forum:
            root_topic_message = get_root_topic_message(update.message)

        text = f"🎊 Congratulations {user}! 🎊\ntelegram-send is now ready for use!"
        print(markup(text, "green"))

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=root_topic_message.message_id if isinstance(root_topic_message, telegram.Message) else None
        )

    config = configparser.ConfigParser()

    if root_topic_message is not None and isinstance(root_topic_message, telegram.Message):
        config["telegram"] = {"TOKEN": token, "chat_id": chat_id, "reply_to_message_id": root_topic_message.message_id}
    else:
        config["telegram"] = {"TOKEN": token, "chat_id": chat_id}
    conf_dir = dirname(conf)
    if conf_dir:
        makedirs(conf_dir, exist_ok=True)
    with open(conf, "w") as f:
        config.write(f)
    if fm_integration:
        if not sys.platform.startswith("win32"):
            return integrate_file_manager()


def integrate_file_manager(clean=False):
    desktop = (
        "[{}]\n"
        "Version=1.0\n"
        "Type=Application\n"
        "Encoding=UTF-8\n"
        "Exec=telegram-send --file %F\n"
        "Icon=telegram\n"
        "Name={}\n"
        "Selection=any\n"
        "Extensions=nodirs;\n"
        "Quote=double\n"
    )
    name = "telegram-send"
    script = """#!/bin/sh
echo "$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS" | sed 's/ /\\\\ /g' | xargs telegram-send -f
"""
    file_managers = [
        ("thunar", "~/.local/share/Thunar/sendto/", "Desktop Entry", "Telegram", ".desktop"),
        ("nemo", "~/.local/share/nemo/actions/", "Nemo Action", "Send to Telegram", ".nemo_action"),
        ("nautilus", "~/.local/share/nautilus/scripts/", "script", "", ""),
    ]
    for (fm, loc, section, label, ext) in file_managers:
        loc = expanduser(loc)
        filename = join(loc, name + ext)
        if not clean:
            if which(fm):
                makedirs(loc, exist_ok=True)
                with open(filename, "w") as f:
                    if section == "script":
                        f.write(script)
                    else:
                        f.write(desktop.format(section, label))
                if section == "script":
                    check_output(["chmod", "+x", filename])
        else:
            if exists(filename):
                remove(filename)


def clean():
    integrate_file_manager(clean=True)
    conf = get_config_path()
    if exists(conf):
        remove(conf)
    if exists(global_config):
        try:
            remove(global_config)
        except OSError:
            print(markup("Can't delete /etc/telegram-send.conf", "red"))
            print(f"Please run: {markup('sudo telegram-send --clean', 'bold')}")
            sys.exit(1)


class ConfigError(Exception):
    pass


class Settings(NamedTuple):
    token: str
    chat_id: int | str
    reply_to_message_id: int | str | None


def get_config_settings(conf=None) -> Settings:
    conf = expanduser(conf) if conf else get_config_path()
    config = configparser.ConfigParser()
    if not config.read(conf) or not config.has_section("telegram"):
        raise ConfigError(f"Config not found: {conf}")

    missing_options = set(["token", "chat_id"]) - set(config.options("telegram"))
    if len(missing_options) > 0:
        raise ConfigError(f"Missing options in config: {', '.join(missing_options)}")

    token = config.get("telegram", "token")
    chat = config.get("telegram", "chat_id")
    reply = config.get("telegram", "reply_to_message_id", fallback=None)

    chat_id = int(chat) if chat.isdigit() else chat
    reply_to_message_id = int(reply) if reply and reply.isdigit() else reply
    return Settings(token=token, chat_id=chat_id, reply_to_message_id=reply_to_message_id)


if __name__ == "__main__":
    main()
