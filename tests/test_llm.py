"""Tests for LLM module (Phase 3)."""
import pytest


def test_build_prompt_raises_not_implemented():
    from app.llm import build_prompt
    with pytest.raises(NotImplementedError):
        build_prompt("question?", [])


def test_query_llm_raises_not_implemented():
    from app.llm import query_llm
    with pytest.raises(NotImplementedError):
        query_llm("prompt")


def test_answer_question_raises_not_implemented():
    from app.llm import answer_question
    with pytest.raises(NotImplementedError):
        answer_question("question?")
