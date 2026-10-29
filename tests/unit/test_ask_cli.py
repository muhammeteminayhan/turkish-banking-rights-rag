"""scripts/ask.py's main(), with a fake database connection, retriever and model."""

import io
import json
from typing import Any

import pytest
from test_generation_pipeline import GOOD, FixedRetriever, ScriptedProvider, _reply

from finhak.generation import cli
from finhak.generation.cli import open_retrieval
from finhak.llm.base import LLMUnavailable
from finhak.llm.factory import ProviderChoice

pytestmark = pytest.mark.unit


class FakeConnection:
    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


@pytest.fixture(autouse=True)
def no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "connect", lambda url: FakeConnection())
    monkeypatch.setattr(cli, "open_retrieval", lambda conn, config, device: FixedRetriever())


def _run(args: list[str], provider: Any) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(args, out=out, provider_factory=lambda: provider, err=err)
    return code, out.getvalue(), err.getvalue()


def test_json_output_is_one_clean_document() -> None:
    code, out, _ = _run(["Kart borcu ertelenirse?", "--json"], ScriptedProvider(_reply([GOOD])))

    assert code == cli.EXIT_OK
    payload = json.loads(out)
    assert payload["status"] == "answered"
    assert payload["citations"][0]["chunk_id"] == "6502:m22:f2"


def test_the_fallback_notice_goes_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    choice = ProviderChoice(ScriptedProvider(_reply([GOOD])), "no Anthropic credentials; Ollama")
    monkeypatch.setattr(cli, "choose_provider", lambda: choice)
    out, err = io.StringIO(), io.StringIO()

    assert cli.main(["Soru?", "--json"], out=out, err=err) == cli.EXIT_OK

    assert "Ollama" in err.getvalue()
    json.loads(out.getvalue())  # still valid JSON


def test_bad_model_settings_exit_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> ProviderChoice:
        raise ValueError("LLM_PROVIDER must be ollama or anthropic")

    monkeypatch.setattr(cli, "choose_provider", broken)

    assert cli.main(["Soru?"], out=io.StringIO(), err=io.StringIO()) == cli.EXIT_FAILED


def test_an_unreachable_model_exits_cleanly() -> None:
    code, out, _ = _run(["Soru?"], ScriptedProvider(LLMUnavailable("ollama is not running")))

    assert (code, out) == (cli.EXIT_FAILED, "")


def test_the_number_of_passages_is_checked() -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["Soru?", "--passages", "0"])


def test_the_retrieval_models_load_on_the_configured_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def made(name: str) -> Any:
        return lambda *args, device: f"{name} on {device}"

    monkeypatch.setattr(cli, "make_embedder", made("bge-m3"))
    monkeypatch.setattr(cli, "CrossEncoderReranker", made("reranker"))
    monkeypatch.setattr(cli, "open_retriever", lambda conn, emb, rr, with_bm25: (emb, rr))

    assert open_retrieval(FakeConnection(), "full", "cpu") == ("bge-m3 on cpu", "reranker on cpu")
    assert open_retrieval(FakeConnection(), "hybrid", "cuda") == ("bge-m3 on cuda", None)


def test_an_unknown_retrieval_device_is_a_settings_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETRIEVAL_DEVICE", "gpu")

    code, _, _ = _run(["Soru?"], ScriptedProvider(_reply([GOOD])))

    assert code == cli.EXIT_FAILED
