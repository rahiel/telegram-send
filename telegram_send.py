#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# telegram-send - Send messages and files over Telegram from the command-line
# Copyright (C) 2016-2019  Rahiel Kasim
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
import configparser
import re
import sys
from os import makedirs, remove
from os.path import dirname, exists, expanduser, join
from random import randint
from shutil import which
from subprocess import check_output
from warnings import warn

import colorama
import telegram
from telegram.constants import MAX_MESSAGE_LENGTH
from appdirs import AppDirs

from version import __version__

try:
    import readline
except ImportError:
    pass

__all__ = ["configure", "send"]

global_config = "/etc/telegram-send.conf"

def main():
    colorama.init()
    parser = argparse.ArgumentParser(description="Send messages and files over Telegram.",
                                     epilog="Homepage: https://github.com/rahiel/telegram-send")
    parser.add_argument("message", help="message(s) to send", nargs="*")
    parser.add_argument("--format", default="text", dest="parse_mode", choices=["text", "markdown", "html"],
                        help="How to format the message(s). Choose from 'text', 'markdown', or 'html'")
    parser.add_argument("--stdin", help="Send text from stdin.", action="store_true")
    parser.add_argument("--pre", help="Send preformatted fixed-width (monospace) text.", action="store_true")
    parser.add_argument("--disable-web-page-preview", help="disable link previews in the message(s)", action="store_true")
    parser.add_argument("--silent", help="send silently, user will receive a notification without sound", action="store_true")
    parser.add_argument("-c", "--configure", help="configure %(prog)s", action="store_true")
    parser.add_argument("--configure-channel", help="configure %(prog)s for a channel", action="store_true")
    parser.add_argument("--configure-group", help="configure %(prog)s for a group", action="store_true")
    parser.add_argument("-f", "--file", help="send file(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-i", "--image", help="send image(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-s", "--sticker", help="send stickers(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--animation", help="send animation(s) (GIF or soundless H.264/MPEG-4 AVC video)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--video", help="send video(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--audio", help="send audio(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-l", "--location", help="send location(s) via latitude and longitude (separated by whitespace or a comma)", nargs="+")
    parser.add_argument("--caption", help="caption for image(s)", nargs="+")
    parser.add_argument("--config", help="specify configuration file", type=str, dest="conf", action="append")
    parser.add_argument("-g", "--global-config", help="Use the global configuration at /etc/telegram-send.conf", action="store_true")
    parser.add_argument("--file-manager", help="Integrate %(prog)s in the file manager", action="store_true")
    parser.add_argument("--clean", help="Clean %(prog)s configuration files.", action="store_true")
    parser.add_argument("--timeout", help="Set the read timeout for network operations. (in seconds)", type=float, default=30.)
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))
    args = parser.parse_args()

    if args.global_config:
        conf = [global_config]
    elif args.conf is None:
        conf = [None]
    else:
        conf = args.conf

    if args.configure:
        return configure(conf[0], fm_integration=True)
    elif args.configure_channel:
        return configure(conf[0], channel=True)
    elif args.configure_group:
        return configure(conf[0], group=True)
    elif args.file_manager:
        if not sys.platform.startswith("win32"):
            return integrate_file_manager()
        else:
            print(markup("File manager integration is unavailable on Windows.", "red"))
            sys.exit(1)
    elif args.clean:
        return clean()

    if args.pre:
        args.parse_mode = "markdown"

    if args.stdin:
        message = sys.stdin.read()
        if len(message) == 0:
            sys.exit(0)
        if args.pre:
            message = pre(message)
        for c in conf:
            send(messages=[message], conf=c, parse_mode=args.parse_mode, silent=args.silent, disable_web_page_preview=args.disable_web_page_preview)

    try:
        if args.pre:
            args.message = [pre(m) for m in args.message]
        for c in conf:
            send(
                messages=args.message,
                conf=c,
                parse_mode=args.parse_mode,
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
    except ConfigError as e:
        print(markup(str(e), "red"))
        cmd = "telegram-send --configure"
        if args.global_config:
            cmd = "sudo " + cmd + " --global-config"
        print("Please run: " + markup(cmd, "bold"))
        sys.exit(1)
    except telegram.error.NetworkError as e:
        if "timed out" in str(e).lower():
            print(markup("Error: Connection timed out", "red"))
            print("Please run with a longer timeout.\n"
                  "Try with the option: " + markup("--timeout {}".format(args.timeout + 10), "bold"))
            sys.exit(1)
        else:
            raise(e)


def send(*,
         messages=None, files=None, images=None, stickers=None, animations=None, videos=None, audios=None,
         captions=None, locations=None, conf=None, parse_mode=None, silent=False, disable_web_page_preview=False,
         timeout=30):
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

    conf (str): Path of configuration file to use. Will use the default config if not specified.
                `~` expands to user's home directory.
    messages (List[str]): The messages to send.
    parse_mode (str): Specifies formatting of messages, one of `["text", "markdown", "html"]`.
    files (List[file]): The files to send.
    images (List[file]): The images to send.
    stickers (List[file]): The stickers to send.
    animations (List[file]): The animations to send.
    videos (List[file]): The videos to send.
    audios (List[file]): The audios to send.
    captions (List[str]): The captions to send with the images/files/animations/videos or audios.
    locations (List[str]): The locations to send. Locations are strings containing the latitude and longitude
                           separated by whitespace or a comma.
    silent (bool): Send silently without sound.
    disable_web_page_preview (bool): Disables web page previews for all links in the messages.
    timeout (int|float): The read timeout for network connections in seconds.
    """
    conf = expanduser(conf) if conf else get_config_path()
    config = configparser.ConfigParser()
    if not config.read(conf) or not config.has_section("telegram"):
        raise ConfigError("Config not found")
    missing_options = set(["token", "chat_id"]) - set(config.options("telegram"))
    if len(missing_options) > 0:
        raise ConfigError("Missing options in config: {}".format(", ".join(missing_options)))
    config = config["telegram"]
    token = config["token"]
    chat_id = int(config["chat_id"]) if config["chat_id"].isdigit() else config["chat_id"]
    request = telegram.utils.request.Request(read_timeout=timeout)
    bot = telegram.Bot(token, request=request)

    # We let the user specify "text" as a parse mode to be more explicit about
    # the lack of formatting applied to the message, but "text" isn't a supported
    # parse_mode in python-telegram-bot. Instead, set the parse_mode to None
    # in this case.
    if parse_mode == "text":
        parse_mode = None

    if messages:
        def send_message(message):
            return bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode, disable_notification=silent, disable_web_page_preview=disable_web_page_preview)

        for m in messages:
            if len(m) > MAX_MESSAGE_LENGTH:
                warn(markup("Message longer than MAX_MESSAGE_LENGTH=%d, splitting into smaller messages." % MAX_MESSAGE_LENGTH, "red"))
                ms = split_message(m, MAX_MESSAGE_LENGTH)
                for m in ms:
                    send_message(m)
            elif len(m) == 0:
                continue
            else:
                send_message(m)

    def make_captions(items, captions):
        captions += [None] * (len(items) - len(captions))  # make captions equal length when not all images/files have captions
        return zip(items, captions)

    if files:
        if captions:
            for (f, c) in make_captions(files, captions):
                bot.send_document(chat_id=chat_id, document=f, caption=c, disable_notification=silent)
        else:
            for f in files:
                bot.send_document(chat_id=chat_id, document=f, disable_notification=silent)

    if images:
        if captions:
            for (i, c) in make_captions(images, captions):
                bot.send_photo(chat_id=chat_id, photo=i, caption=c, disable_notification=silent)
        else:
            for i in images:
                bot.send_photo(chat_id=chat_id, photo=i, disable_notification=silent)

    if stickers:
        for i in stickers:
            bot.send_sticker(chat_id=chat_id, sticker=i, disable_notification=silent)

    if animations:
        if captions:
            for (a, c) in make_captions(animations, captions):
                bot.send_animation(chat_id=chat_id, animation=a, caption=c, disable_notification=silent)
        else:
            for a in animations:
                bot.send_animation(chat_id=chat_id, animation=a, disable_notification=silent)

    if videos:
        if captions:
            for (v, c) in make_captions(videos, captions):
                bot.send_video(chat_id=chat_id, video=v, caption=c, disable_notification=silent)
        else:
            for v in videos:
                bot.send_video(chat_id=chat_id, video=v, disable_notification=silent)

    if audios:
        if captions:
            for (a, c) in make_captions(audios, captions):
                bot.send_audio(chat_id=chat_id, audio=a, caption=c, disable_notification=silent)
        else:
            for a in audios:
                bot.send_audio(chat_id=chat_id, audio=a, disable_notification=silent)

    if locations:
        it = iter(locations)
        for loc in it:
            if "," in loc:
                lat, lon = loc.split(",")
            else:
                lat = loc
                lon = next(it)
            bot.send_location(chat_id=chat_id, latitude=float(lat), longitude=float(lon), disable_notification=silent)


def configure(conf, channel=False, group=False, fm_integration=False):
    """Guide user to set up the bot, saves configuration at `conf`.

    # Arguments

    conf (str): Path where to save the configuration file. May contain `~` for
                user's home.
    channel (Optional[bool]): Configure a channel.
    group (Optional[bool]): Configure a group.
    fm_integration (Optional[bool]): Setup file manager integration.
    """
    conf = expanduser(conf) if conf else get_config_path()
    prompt = "❯ " if not sys.platform.startswith("win32") else "> "
    contact_url = "https://telegram.me/"

    print("Talk with the {} on Telegram ({}), create a bot and insert the token"
          .format(markup("BotFather", "cyan"), contact_url + "BotFather"))
    try:
        token = input(markup(prompt, "magenta")).strip()
    except UnicodeEncodeError:
        # some users can only display ASCII
        prompt = "> "
        token = input(markup(prompt, "magenta")).strip()

    try:
        bot = telegram.Bot(token)
        bot_name = bot.get_me().username
    except:
        print(markup("Something went wrong, please try again.\n", "red"))
        return configure()

    print("Connected with {}.\n".format(markup(bot_name, "cyan")))

    if channel:
        print("Do you want to send to a {} or a {} channel? [pub/priv]"
              .format(markup("public", "bold"), markup("private", "bold")))
        channel_type = input(markup(prompt, "magenta")).strip()
        if channel_type.startswith("pub"):
            print("\nEnter your channel's public name or link:")
            chat_id = input(markup(prompt, "magenta")).strip()
            if "/" in chat_id:
                chat_id = "@" + chat_id.split("/")[-1]
            elif chat_id.startswith("@"):
                pass
            else:
                chat_id = "@" + chat_id
        else:
            print("\nOpen https://web.telegram.org in your browser, sign in and open your private channel."
                  "\nNow copy the URL in the address bar and enter it here:")
            url = input(markup(prompt, "magenta")).strip()
            chat_id = "-100" + re.match(".+web\.telegram\.org\/#\/im\?p=c(\d+)", url).group(1)

        authorized = False
        while not authorized:
            try:
                bot.send_chat_action(chat_id=chat_id, action="typing")
                authorized = True
            except (telegram.error.Unauthorized, telegram.error.BadRequest):
                # Telegram returns a BadRequest when a non-admin bot tries to send to a private channel
                input("Please add {} as administrator to your channel and press Enter"
                      .format(markup(bot_name, "cyan")))
        print(markup("\nCongratulations! telegram-send can now post to your channel!", "green"))
    else:
        password = "".join([str(randint(0, 9)) for _ in range(5)])
        bot_url = contact_url + bot_name
        fancy_bot_name = markup(bot_name, "cyan")
        if group:
            password = "/{}@{}".format(password, bot_name)
            print("Please add {} to your group\nand send the following message to the group: {}\n"
                  .format(fancy_bot_name, markup(password, "bold")))
        else:
            print("Please add {} on Telegram ({})\nand send it the password: {}\n"
                  .format(fancy_bot_name, bot_url, markup(password, "bold")))

        update, update_id = None, None

        def get_user():
            updates = bot.get_updates(offset=update_id, timeout=10)
            for update in updates:
                if update.message:
                    if update.message.text == password:
                        return update, None
            if len(updates) > 0:
                return None, updates[-1].update_id + 1
            else:
                return None, None

        while update is None:
            try:
                update, update_id = get_user()
            except Exception as e:
                print("Error! {}".format(e))

        chat_id = update.message.chat_id
        user = update.message.from_user.username or update.message.from_user.first_name
        m = ("Congratulations {}! ".format(user), "\ntelegram-send is now ready for use!")
        ball = "🎊"
        print(markup("".join(m), "green"))
        bot.send_message(chat_id=chat_id, text=ball + " " + m[0] + ball + m[1])

    config = configparser.ConfigParser()
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
        except PermissionError:
            print(markup("Can't delete /etc/telegram-send.conf", "red"))
            print("Please run: " + markup("sudo telegram-send --clean", "bold"))
            sys.exit(1)


class ConfigError(Exception):
    pass


def markup(text, style):
    ansi_codes = {"bold": "\033[1m", "red": "\033[31m", "green": "\033[32m",
                  "cyan": "\033[36m", "magenta": "\033[35m"}
    return ansi_codes[style] + text + "\033[0m"


def pre(text):
    if "```" in text:
        print(markup("Sending a message containing ``` is not supported with --pre.", "red"))
        sys.exit(1)
    return "```text\n" + text + "```"


def get_config_path():
    return AppDirs("telegram-send").user_config_dir + ".conf"


def split_message(message, max_length):
    """Split large message into smaller messages each smaller than the max_length."""
    ms = []
    while len(message) > max_length:
        ms.append(message[:max_length])
        message = message[max_length:]
    ms.append(message)
    return ms


if __name__ == "__main__":
    main()
