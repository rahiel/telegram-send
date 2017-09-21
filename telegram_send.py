#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# telegram-send - Send messages and files over Telegram from the command-line
# Copyright (C) 2016-2017  Rahiel Kasim
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
import re
import sys
from os import makedirs, remove
from os.path import dirname, exists, expanduser, join
from random import randint
from subprocess import CalledProcessError, check_output
from warnings import warn

import colorama
import telegram
from telegram.constants import MAX_MESSAGE_LENGTH
from appdirs import AppDirs

try:
    import readline
except:
    pass

if sys.version_info >= (3, ):
    import configparser
else:             # python 2.7
    import ConfigParser as configparser
    input = raw_input

__version__ = "0.15"
__all__ = ["configure", "send"]

global_config = "/etc/telegram-send.conf"

def main():
    colorama.init()
    parser = argparse.ArgumentParser(description="Send messages and files over Telegram.",
                                     epilog="Homepage: https://github.com/rahiel/telegram-send")
    parser.add_argument("message", help="message(s) to send", nargs="*")
    parser.add_argument("--format", default="text", dest="parse_mode", choices=["text", "markdown", "html"], help="How to format the message(s). Choose from 'text', 'markdown', or 'html'")
    parser.add_argument("--stdin", help="Send text from stdin.", action="store_true")
    parser.add_argument("--pre", help="Send preformatted fixed-width (monospace) text.", action="store_true")
    parser.add_argument("-c", "--configure", help="configure %(prog)s", action="store_true")
    parser.add_argument("--configure-channel", help="configure %(prog)s for a channel", action="store_true")
    parser.add_argument("--configure-group", help="configure %(prog)s for a group", action="store_true")
    parser.add_argument("-f", "--file", help="send file(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("-i", "--image", help="send image(s)", nargs="+", type=argparse.FileType("rb"))
    parser.add_argument("--caption", help="caption for image(s)", nargs="+")
    parser.add_argument("--config", help="specify configuration file", type=str, dest="conf")
    parser.add_argument("-gc", "--global-config", help="Use the global configuration at /etc/telegram-send.conf", action="store_true")
    parser.add_argument("--file-manager", help="Integrate %(prog)s in the file manager", action="store_true")
    parser.add_argument("--clean", help="Clean %(prog)s configuration files.", action="store_true")
    parser.add_argument("--timeout", help="Set the read timeout for network operations. (in seconds)", type=float, default=30.)
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))
    args = parser.parse_args()

    if args.global_config:
        conf = global_config
    else:
        conf = args.conf

    if args.configure:
        return configure(conf, fm_integration=True)
    elif args.configure_channel:
        return configure(conf, channel=True)
    elif args.configure_group:
        return configure(conf, group=True)
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
        if args.pre:
            message = pre(message)
        return send(messages=[message], parse_mode=args.parse_mode)

    try:
        if args.pre:
            args.message = [pre(m) for m in args.message]
        send(
            messages=args.message,
            conf=conf,
            parse_mode=args.parse_mode,
            files=args.file,
            images=args.image,
            captions=args.caption,
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


def send(messages=None, conf=None, parse_mode=None, files=None, images=None, captions=None, timeout=30):
    """Send data over Telegram. All arguments are optional.

    The `file` type is the [file object][] returned by the `open()` function.
    To send an image/file you open it in binary mode:
    ``` python
    import telegram_send

    with open("image.jpg", "rb") as f:
        telegram_send.send(images=[f])
    ```

    [file object]: https://docs.python.org/3/glossary.html#term-file-object

    # Arguments

    messages (List[str]): The messages to send.
    conf (str): Path of configuration file to use. Will use the default config if not specified.
                `~` expands to user's home directory.
    files (List[file]): The files to send.
    images (List[file]): The images to send.
    captions (List[str]): The captions to send with the images.
    parse_mode (str): Specifies formatting of messages, one of `["text", "markdown", "html"]`.
    timeout (int|float): The read timeout for network connections in seconds.
    """
    conf = expanduser(conf) if conf else get_config_path()
    config = configparser.ConfigParser()
    if not config.read(conf) or not config.has_section("telegram"):
        raise ConfigError("Config not found")
    missing_options = set(["token", "chat_id"]) - set(config.options("telegram"))
    if len(missing_options) > 0:
        raise ConfigError("Missing options in config: {}".format(", ".join(missing_options)))
    token = config.get("telegram", "token")
    chat_id = int(config.get("telegram", "chat_id")) if config.get("telegram", "chat_id").isdigit() else config.get("telegram", "chat_id")

    request = telegram.utils.request.Request(read_timeout=timeout)
    bot = telegram.Bot(token, request=request)

    # We let the user specify "text" as a parse mode to be more explicit about
    # the lack of formatting applied to the message, but "text" isn't a supported
    # parse_mode in python-telegram-bot. Instead, set the parse_mode to None
    # in this case.
    if parse_mode == "text":
        parse_mode = None

    if messages:
        for m in messages:
            if len(m) > MAX_MESSAGE_LENGTH:
                warn(markup("Message longer than MAX_MESSAGE_LENGTH=%d, splitting into smaller messages." % MAX_MESSAGE_LENGTH, "red"))
                ms = split_message(m, MAX_MESSAGE_LENGTH)
                for m in ms:
                    bot.send_message(chat_id=chat_id, text=m, parse_mode=parse_mode)
            else:
                bot.send_message(chat_id=chat_id, text=m, parse_mode=parse_mode)

    if files:
        for f in files:
            bot.send_document(chat_id=chat_id, document=f)

    if images:
        if captions:
            # make captions equal length when not all images have captions
            captions += [None] * (len(images) - len(captions))
            for i, c in zip(images, captions):
                bot.send_photo(chat_id=chat_id, photo=i, caption=c)
        else:
            for i in images:
                bot.send_photo(chat_id=chat_id, photo=i)


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
    config.add_section("telegram")
    config.set("telegram", "TOKEN", token)
    config.set("telegram", "chat_id", str(chat_id))
    # above 3 lines in py3: config["telegram"] = {"TOKEN": token, "chat_id": chat_id}
    conf_dir = dirname(conf)
    if conf_dir:
        makedirs_check(conf_dir)
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
                makedirs_check(loc)
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


def which(p):  # shutil.which in py 3.3+
    try:
        return check_output(["which", p]).decode("utf-8").strip().endswith(p)
    except CalledProcessError:
        return False


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


def makedirs_check(path):
    if not exists(path):  # makedirs has "exist_ok" kw in py 3.2+
        makedirs(path)


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
