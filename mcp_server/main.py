"""A small MCP server with one tool: get_word_definition(word).

MCP (Model Context Protocol) is a standard way to offer tools to an AI
application. This server speaks MCP over "streamable HTTP" at /mcp. The
backend connects to it as an MCP client, lists its tools, and runs them when
Gemini asks for them.

Definitions come from the free Dictionary API (https://dictionaryapi.dev),
which needs no API key. If that API is down or has no entry, a small local
dictionary of common technical terms (local_dictionary.json) is used instead.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dictionary-mcp")

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8001"))
DICTIONARY_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
# Short: if the public API hangs, fall back to the local dictionary quickly
REQUEST_TIMEOUT_SECONDS = 8

# How much of the dictionary entry to return (keeps the LLM prompt small)
MAX_MEANINGS = 3
MAX_DEFINITIONS_PER_MEANING = 2

# Letters (any language), spaces, hyphens and apostrophes; e.g. "well-being", "o'clock"
WORD_PATTERN = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$")

# {"word": [["part of speech", "definition"], ...]}
LOCAL_DICTIONARY: dict[str, list[list[str]]] = json.loads(
    (Path(__file__).parent / "local_dictionary.json").read_text(encoding="utf-8")
)

mcp = FastMCP(
    "dictionary",
    instructions="Looks up English word definitions.",
    host=HOST,
    port=PORT,
    # Each request is independent: no session state to keep between calls
    stateless_http=True,
    json_response=True,
    # Only accept requests addressed to this server's known names
    # (protects against DNS-rebinding attacks from a browser)
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["localhost:*", "127.0.0.1:*", "mcp:*"],
        allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
    ),
)


def _format_online_entry(word: str, entries: list[dict]) -> str:
    """Turn the Dictionary API's JSON into short readable text."""
    entry = entries[0]
    lines = [f"Word: {entry.get('word', word)}"]
    phonetic = entry.get("phonetic")
    if phonetic:
        lines.append(f"Pronunciation: {phonetic}")

    for meaning in entry.get("meanings", [])[:MAX_MEANINGS]:
        part_of_speech = meaning.get("partOfSpeech", "unknown")
        for definition in meaning.get("definitions", [])[:MAX_DEFINITIONS_PER_MEANING]:
            text = definition.get("definition")
            if not text:
                continue
            line = f"- ({part_of_speech}) {text}"
            example = definition.get("example")
            if example:
                line += f' Example: "{example}"'
            lines.append(line)

    lines.append("Source: dictionaryapi.dev")
    return "\n".join(lines)


async def _lookup_online(word: str) -> tuple[str, str | None]:
    """Return (outcome, formatted definition or None). The outcome is logged."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(DICTIONARY_URL.format(word=quote(word)))
    except httpx.HTTPError as exc:
        return f"network_error:{type(exc).__name__}", None

    if response.status_code == 404:
        return "not_found", None
    if response.status_code != 200:
        return f"http_{response.status_code}", None

    try:
        entries = response.json()
        if not isinstance(entries, list) or not entries:
            raise ValueError("unexpected response shape")
        return "found", _format_online_entry(word, entries)
    except ValueError:
        return "bad_response", None


def _lookup_local(word: str) -> str | None:
    senses = LOCAL_DICTIONARY.get(word)
    if not senses:
        return None
    lines = [f"Word: {word}"]
    lines += [f"- ({part_of_speech}) {definition}" for part_of_speech, definition in senses]
    lines.append("Source: built-in technical dictionary")
    return "\n".join(lines)


@mcp.tool()
async def get_word_definition(word: str) -> str:
    """Look up the dictionary definition of an English word.

    Use this when the user asks what a word or term means, e.g.
    "What does authentication mean?" -> word="authentication".

    Args:
        word: A single English word (or short hyphenated/two-word term), without extra text.
    """
    started = time.perf_counter()
    cleaned = " ".join(word.strip().strip("\"'.,?!").split()).lower()

    def log(outcome: str) -> None:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("get_word_definition word=%r outcome=%s duration_ms=%.0f", cleaned, outcome, elapsed_ms)

    if not cleaned or len(cleaned) > 50 or not WORD_PATTERN.match(cleaned):
        log("invalid_input")
        return f'"{word}" is not a valid word to look up. Please provide a single English word.'

    online_outcome, result = await _lookup_online(cleaned)
    if result is not None:
        log("found_online")
        return result

    # API down, erroring, or no entry: try the built-in dictionary
    local_result = _lookup_local(cleaned)
    if local_result is not None:
        log(f"found_local (online: {online_outcome})")
        return local_result

    if online_outcome == "not_found":
        log("not_found")
        return f'No dictionary definition was found for "{cleaned}".'

    log(f"unavailable (online: {online_outcome})")
    return (
        f'No definition for "{cleaned}" is available right now: the online dictionary '
        "could not be reached and the word is not in the built-in dictionary."
    )


if __name__ == "__main__":
    logger.info("Starting dictionary MCP server on http://%s:%s/mcp", HOST, PORT)
    mcp.run(transport="streamable-http")
