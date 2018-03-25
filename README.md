# telegram-send

[![Version](https://img.shields.io/pypi/v/telegram-send.svg)](https://pypi.python.org/pypi/telegram-send)
[![pyversions](https://img.shields.io/pypi/pyversions/telegram-send.svg)](https://pypi.python.org/pypi/telegram-send)
[![Downloads](https://www.cpu.re/static/telegram-send/downloads.svg)](https://www.cpu.re/static/telegram-send/downloads-by-python-version.txt)
[![License](https://img.shields.io/badge/License-GPLv3+-blue.svg)](https://github.com/rahiel/telegram-send/blob/master/LICENSE.txt)

Telegram-send is a command-line tool to send messages and files over Telegram to
your account, to a group or to a channel. It provides a simple interface that
can be easily called from other programs.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-generate-toc again -->
**Table of Contents**

- [Usage](#usage)
- [Installation](#installation)
- [Examples](#examples)
    - [Alert on completion of shell commands](#alert-on-completion-of-shell-commands)
    - [Periodic messages with cron](#periodic-messages-with-cron)
    - [Supervisor process state notifications](#supervisor-process-state-notifications)
    - [Usage from Python](#usage-from-python)
    - [Cron job output](#cron-job-output)
    - [ASCII pictures](#ascii-pictures)
- [Questions & Answers](#questions--answers)
    - [How to use a proxy?](#how-to-use-a-proxy)
- [Uninstallation](#uninstallation)

<!-- markdown-toc end -->

# Usage

To send a message:
``` shell
telegram-send "hello, world"
```
There is a maximum message length of 4096 characters, larger messages will be
automatically split up into smaller ones and sent separately.

To send a message using Markdown or HTML formatting:
```shell
telegram-send --format markdown "Only the *bold* use _italics_"
telegram-send --format html "<pre>fixed-width messages</pre> are <i>also</i> supported"
```
For more information on supported formatting, see the [formatting documentation](https://core.telegram.org/bots/api#formatting-options).

The `--pre` flag formats messages as fixed-width text:
``` shell
telegram-send --pre "monospace"
```

To send a message without link previews:
``` shell
telegram-send --disable-web-page-preview "https://github.com/rahiel/telegram-send"
```

To send a message from stdin:
``` shell
printf 'With\nmultiple\nlines' | telegram-send --stdin
```
With this option you can send the output of any program.

To send a file (maximum file size of 50 MB):
``` shell
telegram-send --file document.pdf
```

To send an image with an optional caption (maximum file size of 10 MB):
``` shell
telegram-send --image photo.jpg --caption "The Moon at night"
```

To send a location via latitude and longitude:
``` shell
telegram-send --location 35.5398033 -79.7488965
```

Telegram-send integrates into your file manager (Thunar, Nautilus and Nemo):

![](https://cloud.githubusercontent.com/assets/6839756/16735957/51c41cf4-478b-11e6-874a-282f559fb9d3.png)

# Installation

Install telegram-send system-wide with pip:
``` shell
sudo pip3 install telegram-send
```

Or if you want to install it for a single user without root permissions:
``` shell
pip3 install telegram-send
```

If installed for a single user you need to add `~/.local/bin` to their path,
refer to this [guide][] for instructions.

And finally configure it with `telegram-send --configure` if you want to send to
your account, `telegram-send --configure-group` to send to a group or with
`telegram-send --configure-channel` to send to a channel.

Use the `--config` option to use multiple configurations. For example to set up
sending to a channel in a non-default configuration: `telegram-send --config
channel.conf --configure-channel`. Then always specify the config file to use
it: `telegram-send --config channel.conf "Bismillah"`.

The `-g` option uses the global configuration at `/etc/telegram-send.conf`.
Configure it once: `sudo telegram-send -g --configure` and all users on the
system can send messages with this config: `telegram-send -g "GNU"` (provided
you've installed it system-wide.)

[guide]: https://www.cpu.re/installing-programs-from-non-system-package-managers-without-sudo/

# Examples

Here are some examples to get a taste of what is possible with telegram-send.

## Alert on completion of shell commands

Receive an alert when long-running commands finish with the `tg` alias, based on
Ubuntu's built-in `alert`. Put the following in your `~/.bashrc`:

``` shell
alias tg='telegram-send "$([ $? = 0 ] && echo "" || echo "error: ") $(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*tg$//'\'')"'
```

And then use it like `sleep 10; tg`. This will send you a message with the
completed command, in this case `sleep 10`.

What if you started a program and forgot to set the alert? Suspend the program
with Ctrl+Z and then enter `fg; telegram-send "your message here"`.

To automatically receive notifications for long running commands, use [ntfy][]
with the Telegram backend.

[ntfy]: https://github.com/dschep/ntfy

## Periodic messages with cron

We can combine telegram-send with [cron][] to periodically send messages. Here
we will set up a cron job to send the [Astronomy Picture of the Day][apod] to
the [astropod][] channel.

Create a bot by talking to the [BotFather][], create a public channel and add
your bot as administrator to the channel. You will need to explicitly search for
your bot's username when adding it. Then run `telegram-send --configure-channel
--config astropod.conf`. We will use the [apod.py][] script that gets the daily
picture and calls telegram-send to post it to the channel.

We create a cron job `/etc/cron.d/astropod` (as root) with the content:

``` shell
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# m h dom mon dow user  command
0 1 * * * telegram ~/apod.py --config ~/astropod.conf
```

Make sure the file ends with a newline. Cron will then execute the script every
day at 1:00 as the user `telegram`. Join the [astropod][] channel to see the
result.

[cron]: https://en.wikipedia.org/wiki/Cron
[apod]: http://apod.nasa.gov/apod/astropix.html
[astropod]: https://telegram.me/astropod
[botfather]: https://telegram.me/botfather
[apod.py]: https://github.com/rahiel/telegram-send/blob/master/examples/apod.py

## Supervisor process state notifications

[Supervisor][] controls and monitors processes. It can start processes at boot,
restart them if they fail and also report on their status. [Supervisor-alert][]
is a simple plugin for Supervisor that sends messages on process state updates
to an arbitrary program. Using it with telegram-send (by using the `--telegram`
option), you can receive notifications whenever one of your processes exits.

[supervisor]: http://supervisord.org
[supervisor-alert]: https://github.com/rahiel/supervisor-alert

## Usage from Python

Because telegram-send is written in Python, you can use its functionality
directly from other Python programs: `import telegram_send`. Look at the
[documentation](https://www.cpu.re/telegram-send/docs/api/).

## Cron job output

Cron has a built-in feature to send the output of jobs via mail. In this example
we'll send cron output over Telegram. Here is the example cron job:

``` shell
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# m h dom mon dow user  command
0 * * * * rahiel chronic ~/script.bash 2>&1 | telegram-send -g --stdin
```

The command is `chronic ~/script.bash 2>&1 | telegram-send -g --stdin`. We run
the cron job with `chronic`, a tool from [moreutils][]. Chronic makes sure that
a command produces no output unless it fails. No news is good news! If our
script fails, chronic passes the output through the pipe (`|`) to telegram-send.
We also send the output of stderr by redirecting stderr to stdout (`2>&1`).

Here we've installed telegram-send system-wide with `sudo` and use the global
configuration (`-g`) so `telegram-send` is usable in the cron job. Place the
cron job in `/etc/cron.d/` and make sure the file ends with a newline. The
filename can't contain a `.` either.

[moreutils]: https://joeyh.name/code/moreutils/

## ASCII pictures

Combining `--stdin` and `--pre`, we can send ASCII pictures:

``` shell
ncal -bh | telegram-send --pre --stdin
apt-get moo | telegram-send --pre --stdin
```

# Questions & Answers

## How to use a proxy?

You can set a proxy with an environment variable:
``` shell
https_proxy=https://ip:port telegram-send "hello"
```

Within Python you can set the environment variable with:
``` python
os.environ["https_proxy"] = "https://ip:port"
```

If you have a SOCKS proxy, you need to install support for it:
``` python
pip3 install pysocks
```
If you installed `telegram-send` with `sudo`, you also need to install `pysocks`
with `sudo`.

# Uninstallation

``` shell
sudo telegram-send --clean
sudo pip3 uninstall telegram-send
```

Or if you installed it for a single user:
``` shell
telegram-send --clean
pip3 uninstall telegram-send
```
