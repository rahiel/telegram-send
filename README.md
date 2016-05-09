# telegram-send

[![License](https://img.shields.io/badge/License-GPLv3+-blue.svg)](https://github.com/rahiel/telegram-send/blob/master/LICENSE.txt)

Telegram-send is a command-line tool to send messages and files over Telegram to
your account. It provides a simple interface that can be easily called from
other programs.

# Usage

To send a message:
``` shell
telegram-send "hello, world"
```

To send a file:
``` shell
telegram-send --file document.pdf
```

# Install

Install telegram-send system-wide with pip:
``` shell
sudo pip3 install telegram-send
```

Or if you want to install it for a single user:
``` shell
pip3 install telegram-send
```

If installed for a single user you need to add `~/.local/bin` to their path:
``` shell
echo 'PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

And finally configure it with `telegram-send --configure` and follow the
instructions.

# Uninstall

``` shell
sudo pip3 uninstall telegram-send
sudo rm /etc/telegram-send.conf
```

Or if you installed it for a single user:
``` shell
pip3 uninstall telegram-send
rm ~/.config/telegram-send.conf
```
