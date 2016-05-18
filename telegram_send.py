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
import configparser
from os.path import expanduser
from random import randint
import sys

import telegram

__version__ = "0.5"


def main():
    parser = argparse.ArgumentParser(description="Send messages and files over Telegram.",
                                     epilog="Homepage: https://github.com/rahiel/telegram-send")
    parser.add_argument("message", help="message(s) to send", nargs='*')
    parser.add_argument("-c", "--configure", help="configure %(prog)s", action="store_true")
    parser.add_argument("--configure-channel", help="configure %(prog)s for a channel", action="store_true")
    parser.add_argument("-f", "--file", help="send file(s)", nargs='+', type=argparse.FileType("rb"))
    parser.add_argument("-i", "--image", help="send image(s)", nargs='+', type=argparse.FileType("rb"))
    parser.add_argument("--caption", help="caption for image(s)", nargs='+')
    parser.add_argument("--config", help="specify configuration file", type=str, dest="conf")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))
    args = parser.parse_args()

    if args.configure:
        return configure(args.conf)
    elif args.configure_channel:
        return configure(args.conf, channel=True)

    try:
        send(messages=args.message, conf=args.conf, files=args.file, images=args.image, captions=args.caption)
    except ConfigError as e:
        print(markup(str(e), "red"))
        cmd = "telegram-send --configure"
        if get_config_path().startswith("/etc/"):
            cmd = "sudo " + cmd
        print("Please run: " + markup(cmd, "bold"))


def send(messages=None, conf=None, files=None, images=None, captions=None):
    """Send data over Telegram.

    Optional Args:
        messages (List[str])
        conf (str): Path of configuration file to use. Will use the default config if not specified.
            '~' expands to user's home.
        files (List[file])
        images (List[file])
        captions (List[str])
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

    bot = telegram.Bot(token)

    if messages:
        for m in messages:
            bot.sendMessage(chat_id=chat_id, text=m)

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


def configure(conf, channel=False):
    """Guide user to set up the bot, saves configuration at conf.

    Args:
        conf (str): Path where to save the configuration file. May contain '~' for user's home.
        channel (Optional[bool]): Whether to configure a channel or not.
    """
    conf = expanduser(conf) if conf else get_config_path()
    prompt = "❯ "
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
        ball = telegram.Emoji.CONFETTI_BALL
        print(markup("".join(m), "green"))
        bot.sendMessage(chat_id=chat_id, text=ball + ' ' + m[0] + ball + m[1])

    config = configparser.ConfigParser()
    config["telegram"] = {"TOKEN": token, "chat_id": chat_id}
    with open(conf, 'w') as f:
        config.write(f)


class ConfigError(Exception):
    pass


def markup(text, style):
    ansi_codes = {"bold": "\033[1m", "red": "\033[31m", "green": "\033[32m",
                  "cyan": "\033[36m", "magenta": "\033[35m"}
    return ansi_codes[style] + text + "\033[0m"


def get_config_path():
    """Config file is in /etc/ if the script is installed system-wide,
    otherwise in user's home directory.
    """
    conf = "telegram-send.conf"
    path = sys.path[0]
    if path.startswith("/home/") or path.startswith("/Users/"):
        return expanduser("~/.config/" + conf)
    else:
        return "/etc/" + conf
