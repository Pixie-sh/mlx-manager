from __future__ import annotations

import json

import pytest

from mlx_manager import bot as bot_mod


def _make_model(path):
    path.mkdir(parents=True)
    (path / "config.json").write_text(json.dumps({"model_type": "gemma"}))
    (path / "model.safetensors").write_bytes(b"")


def test_resolve_model_uses_existing_local_dir(tmp_path):
    local = tmp_path / "my-model"
    _make_model(local)
    # An absolute, complete local dir is returned as-is, no download attempted.
    assert bot_mod.resolve_model(str(local), str(tmp_path / "bot")) == str(local)


def test_resolve_model_reuses_cached_repo_without_network(tmp_path):
    cache = tmp_path / "bot"
    # Pre-seed the cache as if a prior run already downloaded it.
    cached = cache / "mlx-community--gemma-4-e2b-it-4bit"
    _make_model(cached)
    # snapshot_download must NOT be called when the model is already present.
    result = bot_mod.resolve_model("mlx-community/gemma-4-e2b-it-4bit", str(cache))
    assert result == str(cached)


def test_resolve_model_downloads_once_when_missing(tmp_path, monkeypatch):
    cache = tmp_path / "bot"
    calls = []

    def fake_snapshot_download(repo_id, local_dir):
        calls.append((repo_id, local_dir))
        from pathlib import Path

        _make_model(Path(local_dir))
        return local_dir

    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot_download)

    result = bot_mod.resolve_model(
        "mlx-community/gemma-4-e2b-it-4bit", str(cache), on_status=lambda _m: None
    )
    expected = cache / "mlx-community--gemma-4-e2b-it-4bit"
    assert result == str(expected)
    assert calls == [("mlx-community/gemma-4-e2b-it-4bit", str(expected))]


def test_build_system_prompt_with_and_without_context():
    status = [{"running": True, "port": 1235, "model_alias": "qwen", "endpoint_ok": True, "health": "ok"}]
    doctor = [{"name": "python", "status": "OK", "detail": "ok"}]
    full = bot_mod.build_system_prompt(status, doctor)
    assert "port 1235" in full and "Running servers" in full
    bare = bot_mod.build_system_prompt(status, doctor, with_context=False)
    assert "Running servers" not in bare


def test_select_model_override_wins(tmp_path):
    bot_mod.save_selection(str(tmp_path), "saved/model")
    assert bot_mod.select_model("cli/override", "default/model", str(tmp_path)) == "cli/override"


def test_select_model_uses_saved_selection(tmp_path):
    bot_mod.save_selection(str(tmp_path), "saved/model")
    assert bot_mod.select_model(None, "default/model", str(tmp_path)) == "saved/model"


def test_select_model_uses_default_if_already_downloaded(tmp_path):
    _make_model(tmp_path / "default--model")
    assert bot_mod.select_model(None, "default/model", str(tmp_path)) == "default/model"


def test_select_model_returns_none_for_first_run(tmp_path):
    assert bot_mod.select_model(None, "default/model", str(tmp_path)) is None


def test_choose_model_empty_picks_default():
    chosen = bot_mod.choose_model(
        "mlx-community/Qwen3-1.7B-4bit",
        input_fn=lambda _p: "",
        out_fn=lambda _m: None,
    )
    assert chosen == "mlx-community/Qwen3-1.7B-4bit"


def test_choose_model_numeric_pick():
    chosen = bot_mod.choose_model(
        bot_mod.BOT_MODELS[0]["id"],
        input_fn=lambda _p: "2",
        out_fn=lambda _m: None,
    )
    assert chosen == bot_mod.BOT_MODELS[1]["id"]


def test_choose_model_custom_repo_id():
    chosen = bot_mod.choose_model(
        bot_mod.BOT_MODELS[0]["id"],
        input_fn=lambda _p: "some-org/custom-model",
        out_fn=lambda _m: None,
    )
    assert chosen == "some-org/custom-model"


def test_choose_model_menu_lists_all_options():
    lines = []
    bot_mod.choose_model(
        bot_mod.BOT_MODELS[0]["id"],
        input_fn=lambda _p: "1",
        out_fn=lines.append,
    )
    rendered = "\n".join(lines)
    for m in bot_mod.BOT_MODELS:
        assert m["label"] in rendered
    assert "(default)" in rendered


def test_build_system_prompt_flags_unhealthy_server():
    status = [{
        "running": True, "port": 1236, "model_alias": "deepseek",
        "endpoint_ok": True, "health": "error",
        "health_detail": "model architecture 'deepseek_v4' is not supported",
    }]
    prompt = bot_mod.build_system_prompt(status, [])
    assert "deepseek_v4" in prompt and "ERROR" in prompt
