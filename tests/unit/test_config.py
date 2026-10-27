from pathlib import Path

import pytest

from finhak.config import DEFAULT_DATABASE_URL, database_url, merged_env, read_env_file

pytestmark = pytest.mark.unit


def test_the_environment_wins_over_the_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://file/db\n", encoding="utf-8")

    assert database_url({"DATABASE_URL": "postgresql://env/db"}, env_file) == "postgresql://env/db"


def test_the_env_file_is_used_when_the_environment_has_no_value(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n\nOTHER=1\nnot a setting\nDATABASE_URL = 'postgresql://file/db'\n",
        encoding="utf-8",
    )

    assert database_url({"DATABASE_URL": ""}, env_file) == "postgresql://file/db"
    assert read_env_file(env_file) == {"OTHER": "1", "DATABASE_URL": "postgresql://file/db"}


def test_export_lines_and_inline_comments_are_understood(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "export DATABASE_URL=postgresql://a/b  # local db\nQUOTED='x # not a comment'\n",
        encoding="utf-8",
    )

    assert read_env_file(env_file) == {
        "DATABASE_URL": "postgresql://a/b",
        "QUOTED": "x # not a comment",
    }


def test_merged_env_lets_set_variables_win_over_the_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_PROVIDER=anthropic\nOLLAMA_MODEL=qwen3:8b\n", encoding="utf-8")

    merged = merged_env({"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": ""}, env_file)

    assert merged["LLM_PROVIDER"] == "ollama"
    assert merged["OLLAMA_MODEL"] == "qwen3:8b"  # an empty variable does not hide the file


def test_the_default_matches_docker_compose(tmp_path: Path) -> None:
    assert database_url({}, tmp_path / "missing.env") == DEFAULT_DATABASE_URL
    assert DEFAULT_DATABASE_URL.endswith("@127.0.0.1:5433/finhak")
