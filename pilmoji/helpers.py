from __future__ import annotations

import re

from enum import Enum

import emoji

import PIL
from PIL import ImageFont

from typing import Dict, Final, List, NamedTuple, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .core import FontT

# This is actually way faster than it seems
# Create a dictionary mapping English emoji descriptions to their unicode representations
# Only include emojis that have an English description and are fully qualified
language_pack: Dict[str, str] = {
    data["en"]: emj
    for emj, data in emoji.EMOJI_DATA.items()
    if "en" in data and data["status"] <= emoji.STATUS["fully_qualified"]
}
_UNICODE_EMOJI_REGEX = "|".join(
    map(re.escape, sorted(language_pack.values(), key=len, reverse=True))
)
_DISCORD_EMOJI_REGEX = "<a?:[a-zA-Z0-9_]{1,32}:[0-9]{17,22}>"
_CUSTOM_EMOJI_REGEX = "<:[a-zA-Z0-9_-]{1,32}:>"

EMOJI_REGEX: Final[re.Pattern[str]] = re.compile(
    f"({_UNICODE_EMOJI_REGEX}|{_DISCORD_EMOJI_REGEX}|{_CUSTOM_EMOJI_REGEX})"
)
UNICODE_EMOJI_REGEX = re.compile(_UNICODE_EMOJI_REGEX)
DISCORD_EMOJI_REGEX = re.compile(_DISCORD_EMOJI_REGEX)
CUSTOM_EMOJI_REGEX = re.compile(_CUSTOM_EMOJI_REGEX)

__all__ = (
    "EMOJI_REGEX",
    "UNICODE_EMOJI_REGEX",
    "DISCORD_EMOJI_REGEX",
    "CUSTOM_EMOJI_REGEX",
    "Node",
    "NodeType",
    "to_nodes",
    "getsize",
)


class NodeType(Enum):
    """|enum|

    Represents the type of a :class:`~.Node`.

    Attributes
    ----------
    text
        This node is a raw text node.
    emoji
        This node is a unicode emoji.
    discord_emoji
        This node is a Discord emoji.
    custom_emoji
        This node is a custom emoji.
    """

    text = 0
    emoji = 1
    discord_emoji = 2
    custom_emoji = 3


class Node(NamedTuple):
    """Represents a parsed node inside of a string.

    Attributes
    ----------
    type: :class:`~.NodeType`
        The type of this node.
    content: str
        The contents of this node.
    """

    type: NodeType
    content: str

    def __repr__(self) -> str:
        return f"<Node type={self.type.name!r} content={self.content!r}>"


def _parse_line(line: str, /) -> List[Node]:
    nodes = []

    for i, chunk in enumerate(EMOJI_REGEX.split(line)):
        if not chunk:
            continue

        if DISCORD_EMOJI_REGEX.match(chunk):
            node = Node(NodeType.discord_emoji, chunk.split(":")[-1][:-1])
        elif CUSTOM_EMOJI_REGEX.match(chunk):
            node = Node(NodeType.custom_emoji, chunk[2:-2])
        elif UNICODE_EMOJI_REGEX.match(chunk):
            node = Node(NodeType.emoji, chunk)
        else:
            node = Node(NodeType.text, chunk)

        nodes.append(node)

    return nodes


def to_nodes(text: str, /) -> List[List[Node]]:
    """Parses a string of text into :class:`~.Node`s.

    This method will return a nested list, each element of the list
    being a list of :class:`~.Node`s and representing a line in the string.

    The string ``'Hello\nworld'`` would return something similar to
    ``[[Node('Hello')], [Node('world')]]``.

    Parameters
    ----------
    text: str
        The text to parse into nodes.

    Returns
    -------
    List[List[:class:`~.Node`]]
    """
    return [_parse_line(line) for line in text.splitlines()]


def getsize(
    text: str, font: FontT = None, *, spacing: int = 4, emoji_scale_factor: float = 1
) -> Tuple[int, int]:
    """Return the width and height of the text when rendered.
    This method supports multiline text.

    Parameters
    ----------
    text: str
        The text to use.
    font
        The font of the text.
    spacing: int
        The spacing between lines, in pixels.
        Defaults to `4`.
    emoji_scale_factor: float
        The rescaling factor for emojis.
        Defaults to `1`.
    """
    if font is None:
        font = ImageFont.load_default()

    x, y = 0, 0
    nodes = to_nodes(text)

    for line in nodes:
        this_x = 0
        for node in line:
            content = node.content

            if node.type is not NodeType.text:
                width = int(emoji_scale_factor * font.size)
            elif tuple(int(part) for part in PIL.__version__.split(".")) >= (9, 2, 0):
                width = int(font.getlength(content))
            else:
                width, _ = font.getsize(content)

            this_x += width

        y += spacing + font.size

        if this_x > x:
            x = this_x

    return x, y - spacing
