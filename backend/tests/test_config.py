import os
from pathlib import Path

from netbox.config import clean_env_value, load_env_file, load_env_files, resolve_project_path, target_to_arg


def test_clean_env_value_strips_matching_quotes() -> None:
    assert clean_env_value('"Netbox"') == "Netbox"
    assert clean_env_value("'Netbox'") == "Netbox"
    assert clean_env_value("Netbox") == "Netbox"


def test_load_env_file_preserves_shell_values(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NETBOX_PORT=5000\nNETBOX_HOST=0.0.0.0\n")
    monkeypatch.delenv("NETBOX_HOST", raising=False)
    monkeypatch.setenv("NETBOX_PORT", "4177")

    load_env_file(env_file, set(os.environ))

    assert os.environ["NETBOX_PORT"] == "4177"
    assert os.environ["NETBOX_HOST"] == "0.0.0.0"
    monkeypatch.delenv("NETBOX_HOST", raising=False)


def test_load_env_files_supports_environment_local_overrides(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".env").write_text("NETBOX_ENV=production\nNETBOX_PORT=4177\n")
    (tmp_path / ".env.local").write_text("NETBOX_PORT=5177\n")
    (tmp_path / ".env.production").write_text("NETBOX_HOST=0.0.0.0\n")
    (tmp_path / ".env.production.local").write_text("NETBOX_HOST=127.0.0.1\n")
    monkeypatch.delenv("NETBOX_ENV", raising=False)
    monkeypatch.delenv("NETBOX_PORT", raising=False)
    monkeypatch.delenv("NETBOX_HOST", raising=False)

    load_env_files(tmp_path)

    assert os.environ["NETBOX_PORT"] == "5177"
    assert os.environ["NETBOX_HOST"] == "127.0.0.1"


def test_target_to_arg_uses_structured_target_config() -> None:
    assert target_to_arg({"host": "1.1.1.1", "label": "Cloudflare DNS", "scope": "external"}) == (
        "1.1.1.1:Cloudflare DNS:external"
    )


def test_resolve_project_path_keeps_absolute_paths(tmp_path: Path) -> None:
    assert resolve_project_path(str(tmp_path)) == str(tmp_path)
