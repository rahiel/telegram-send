import html

from platformdirs import user_config_dir


def markup(text: str, style: str) -> str:
    ansi_codes = {"bold": "\033[1m", "red": "\033[31m", "green": "\033[32m",
                  "cyan": "\033[36m", "magenta": "\033[35m"}
    return ansi_codes[style] + text + "\033[0m"


def pre_format(text: str) -> str:
    escaped_text = html.escape(text)
    return f"<pre>{escaped_text}</pre>"


def split_message(message: str, max_length: int) -> list[str]:
    """Split large message into smaller messages each smaller than the max_length."""
    ms = []
    while len(message) > max_length:
        ms.append(message[:max_length])
        message = message[max_length:]
    ms.append(message)
    return ms


def get_config_path() -> str:
    return user_config_dir("telegram-send") + ".conf"
