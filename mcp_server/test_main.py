"""Unit tests for the dictionary tool. Run from mcp_server/: python -m pytest"""

import asyncio

import main


def run(word, monkeypatch, online=("not_found", None)):
    async def fake_online(cleaned):
        return online

    monkeypatch.setattr(main, "_lookup_online", fake_online)
    return asyncio.run(main.get_word_definition(word))


def test_online_result_is_used_first(monkeypatch):
    result = run("Authentication?", monkeypatch, online=("found", "Word: authentication\n- online"))
    assert "online" in result


def test_falls_back_to_local_dictionary_when_api_is_down(monkeypatch):
    result = run("authentication", monkeypatch, online=("network_error:ReadTimeout", None))
    assert "verifying" in result
    assert "built-in technical dictionary" in result


def test_not_found(monkeypatch):
    result = run("qwxyzzt", monkeypatch, online=("not_found", None))
    assert result == 'No dictionary definition was found for "qwxyzzt".'


def test_unavailable_and_unknown(monkeypatch):
    result = run("qwxyzzt", monkeypatch, online=("http_522", None))
    assert "could not be reached" in result


def test_invalid_input_is_rejected_without_lookup(monkeypatch):
    def fail(_):
        raise AssertionError("should not look up")

    monkeypatch.setattr(main, "_lookup_online", fail)
    assert "not a valid word" in asyncio.run(main.get_word_definition("drop table; 123"))


def test_formats_online_entry():
    entries = [
        {
            "word": "hello",
            "phonetic": "/həˈləʊ/",
            "meanings": [
                {"partOfSpeech": "noun", "definitions": [{"definition": "A greeting.", "example": "She said hello."}]}
            ],
        }
    ]
    text = main._format_online_entry("hello", entries)
    assert "(noun) A greeting." in text
    assert "dictionaryapi.dev" in text
