# -*- coding: utf-8 -*-
# telegram-send - Send messages and files over Telegram from the command-line
# Copyright (C) 2016  Rahiel Kasim
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
from os import makedirs, remove
from os.path import expanduser, join, exists
from random import randint
import sys
from subprocess import check_output, CalledProcessError

from appdirs import AppDirs
from colorama import init
import telegram

if sys.version_info >= (3, ):
    import configparser
else:             # python 2.7
    import ConfigParser as configparser
    input = raw_input

__version__ = "0.8.4"

init()


def main():
    parser = argparse.ArgumentParser(description="Send messages and files over Telegram.",
                                     epilog="Homepage: https://github.com/rahiel/telegram-send")
    parser.add_argument("message", help="message(s) to send", nargs='*')
    parser.add_argument("-c", "--configure", help="configure %(prog)s", action="store_true")
    parser.add_argument("--configure-channel", help="configure %(prog)s for a channel", action="store_true")
    parser.add_argument("--format", default="text", dest="parse_mode", choices=['text', 'markdown', 'html'], help="How to format the message(s). Choose from 'text', 'markdown', or 'html'")
    parser.add_argument("-f", "--file", help="send file(s)", nargs='+', type=argparse.FileType("rb"))
    parser.add_argument("-i", "--image", help="send image(s)", nargs='+', type=argparse.FileType("rb"))
    parser.add_argument("--caption", help="caption for image(s)", nargs='+')
    parser.add_argument("--config", help="specify configuration file", type=str, dest="conf")
    parser.add_argument("--file-manager", help="Integrate %(prog)s in the file manager", action="store_true")
    parser.add_argument("--clean", help="Clean %(prog)s configuration files.", action="store_true")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))
    args = parser.parse_args()

    if args.configure:
        return configure(args.conf, fm_integration=True)
    elif args.configure_channel:
        return configure(args.conf, channel=True)
    elif args.file_manager:
        return integrate_file_manager()
    elif args.clean:
        return clean()

    try:
        send(messages=args.message, conf=args.conf, parse_mode=args.parse_mode, files=args.file, images=args.image, captions=args.caption)
    except ConfigError as e:
        print(markup(str(e), "red"))
        cmd = "telegram-send --configure"
        if get_config_path().startswith("/etc/"):
            cmd = "sudo " + cmd
        print("Please run: " + markup(cmd, "bold"))


def send(messages=None, conf=None, parse_mode=None, files=None, images=None, captions=None):
    """Send data over Telegram.

    Optional Args:
        messages (List[str])
        conf (str): Path of configuration file to use. Will use the default config if not specified.
            '~' expands to user's home.
        files (List[file])
        images (List[file])
        captions (List[str])
        parse_mode (str): specifies formatting of messages, an element of {"text", "markdown", "html"}
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

    bot = telegram.Bot(token)

    # We let the user specify "text" as a parse mode to be more explicit about
    # the lack of formatting applied to the message, but "text" isn't a supported
    # parse_mode in python-telegram-bot. Instead, set the parse_mode to None
    # in this case.
    if parse_mode == "text":
        parse_mode = None

    if messages:
        for m in messages:
            bot.sendMessage(chat_id=chat_id, text=m, parse_mode=parse_mode)

    if files:
        for f in files:
            bot.sendDocument(chat_id=chat_id, document=f)

    if images:
        if captions:
            # make captions equal length when not all images have captions
            captions += [None] * (len(images) - len(captions))
            for i, c in zip(images, captions):
                bot.sendPhoto(chat_id=chat_id, photo=i, caption=c)
        else:
            for i in images:
                bot.sendPhoto(chat_id=chat_id, photo=i)


def configure(conf, channel=False, fm_integration=False):
    """Guide user to set up the bot, saves configuration at conf.

    Args:
        conf (str): Path where to save the configuration file. May contain '~' for user's home.
        channel (Optional[bool]): Whether to configure a channel or not.
    """
    conf = expanduser(conf) if conf else get_config_path()
    prompt = "❯ " if not sys.platform.startswith("win32") else "> "
    contact_url = "https://telegram.me/"

    print("Talk with the {} on Telegram ({}), create a bot and insert the token"
          .format(markup("BotFather", "cyan"), contact_url + "BotFather"))
    token = input(markup(prompt, "magenta")).strip()

    try:
        bot = telegram.Bot(token)
        bot_name = bot.getMe().username
    except:
        print(markup("Something went wrong, please try again.\n", "red"))
        return configure()

    print("Connected with {}.\n".format(markup(bot_name, "cyan")))

    if channel:
        print("Enter your channel's public name or link:"
              .format(markup(bot_name, "cyan")))
        chat_id = input(markup(prompt, "magenta")).strip()
        if "telegram.me" in chat_id:
            chat_id = '@' + chat_id.split('/')[-1]
        elif chat_id.startswith('@'):
            pass
        else:
            chat_id = '@' + chat_id

        authorized = False
        while not authorized:
            try:
                bot.sendChatAction(chat_id=chat_id, action="typing")
                authorized = True
            except telegram.error.Unauthorized:
                input("Please add {} as administrator to {} and press Enter"
                      .format(markup(bot_name, "cyan"), markup(chat_id, "cyan")))
        print(markup("\nCongratulations! telegram-send can now post to {}".format(chat_id), "green"))
    else:
        password = "".join([str(randint(0, 9)) for _ in range(5)])
        print("Please add {} on Telegram ({})\nand send it the password: {}\n"
              .format(markup(bot_name, "cyan"), contact_url + bot_name, markup(password, "bold")))

        update, update_id = None, None

        def get_user():
            updates = bot.getUpdates(offset=update_id, timeout=10)
            for update in updates:
                # print(update.message.text)
                if update.message.text.strip() == password:
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
        bot.sendMessage(chat_id=chat_id, text=ball + ' ' + m[0] + ball + m[1])

    config = configparser.ConfigParser()
    config.add_section("telegram")
    config.set("telegram", "TOKEN", token)
    config.set("telegram", "chat_id", str(chat_id))
    # above 3 lines in py3: config["telegram"] = {"TOKEN": token, "chat_id": chat_id}
    with open(conf, 'w') as f:
        config.write(f)
    if fm_integration:
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
                if not exists(loc):  # makedirs has "exist_ok" kw in py 3.2+
                    makedirs(loc)
                with open(filename, 'w') as f:
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


class ConfigError(Exception):
    pass


def markup(text, style):
    ansi_codes = {"bold": "\033[1m", "red": "\033[31m", "green": "\033[32m",
                  "cyan": "\033[36m", "magenta": "\033[35m"}
    return ansi_codes[style] + text + "\033[0m"


def get_config_path():
    return AppDirs("telegram-send").user_config_dir + ".conf"
