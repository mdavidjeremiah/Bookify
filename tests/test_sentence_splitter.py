"""Tests for sentence splitting and text cleaning."""

import pytest
from readaloud.loaders.sentence_splitter import clean_text, split_sentences


def test_split_sentences_basic():
    text = "This is the first sentence. Here is the second sentence! Is this the third?"
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "This is the first sentence."
    assert sentences[1] == "Here is the second sentence!"
    assert sentences[2] == "Is this the third?"


def test_split_sentences_with_abbreviations():
    text = "Dr. Smith met with Mr. Jones at the clinic. They reviewed the report."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "Dr. Smith met with Mr. Jones at the clinic." in sentences[0]
    assert "They reviewed the report." in sentences[1]


def test_split_sentences_with_quotes():
    text = '"Hello world!" She said with enthusiasm. Everything was quiet.'
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == '"Hello world!"'
    assert sentences[1] == "She said with enthusiasm."
    assert sentences[2] == "Everything was quiet."


def test_clean_text_dehyphenation():
    raw = "The infor-\nmation was trans-\nmitted properly."
    cleaned = clean_text(raw)
    assert "information" in cleaned
    assert "transmitted" in cleaned


def test_clean_text_removes_standalone_page_numbers():
    raw = "Header text.\n\n42\n\nNext paragraph begins here."
    cleaned = clean_text(raw)
    assert "42" not in cleaned.split()
    assert "Header text" in cleaned
    assert "Next paragraph begins here" in cleaned


def test_clean_text_collapses_whitespace():
    raw = "Too   many    spaces   and\n\n\n\nmany breaks."
    cleaned = clean_text(raw)
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned
