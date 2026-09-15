"""Tests for the three-way question intent gate used by /chat."""

import pytest

from app.services.domain_filter import (
    OFFTOPIC_RESPONSE,
    SMALLTALK_RESPONSE,
    classify_question,
    is_career_related,
)


@pytest.mark.parametrize("question", [
    "hi", "hii", "hello", "hey there", "yo", "good morning", "good evening",
    "thanks!", "thank you", "cheers", "bye",
    "who are you", "what can you do", "what are you", "how are you",
    "help",
])
def test_greetings_are_smalltalk_not_refused(question):
    assert classify_question(question) == "smalltalk"


@pytest.mark.parametrize("question", [
    "what are my recent internship emails",
    "did I get any offers?",
    "when is the application deadline",
    "any interview scheduled this week",
    "what did the recruiter say",
    "show me the latest emails",
    "what's the status of my applications",
    "any inetrn opportunities",          # typo tolerated by the fuzzy pass
])
def test_career_questions_reach_the_agent(question):
    assert classify_question(question) == "career"


@pytest.mark.parametrize("question", [
    "what is the weather tomorrow",
    "give me a pasta recipe",
    "who won the world cup",
    "write me a poem about the sea",
    "What did I order on Amazon last week?",
    "When is my flight to Boston?",
    "tell me about control systems",     # 'control' must not match 'role'
    "my drone follows a patrol route",   # 'patrol' must not match 'role'
])
def test_offtopic_questions_are_refused(question):
    assert classify_question(question) == "offtopic"


def test_career_intent_wins_over_greeting():
    """A greeting attached to a real question must still be answered."""
    assert classify_question("hi, any internship offers?") == "career"


def test_responses_are_distinct():
    assert SMALLTALK_RESPONSE != OFFTOPIC_RESPONSE
    assert "only answer questions related to your career" in OFFTOPIC_RESPONSE
    assert "internship" in SMALLTALK_RESPONSE


def test_inbox_vocabulary_does_not_leak_into_ingestion():
    """
    Generic inbox words widen the QUESTION gate but must never widen the
    EMAIL gate, or non-career mail would get indexed.
    """
    assert is_career_related(
        "Your monthly subscription receipt",
        "billing@streamflix.com",
        "Your card was charged. View your invoice in account settings.",
    ) is False

    assert is_career_related(
        "10 pasta recipes for the weekend",
        "newsletter@cookingweekly.com",
        "This week we cover carbonara and cacio e pepe.",
    ) is False

    assert is_career_related(
        "Internship offer — Backend Engineering Intern",
        "hr@nimbusworks.com",
        "We are delighted to extend an internship offer.",
    ) is True
