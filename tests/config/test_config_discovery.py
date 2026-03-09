from pathlib import Path

from termlint.config import TermlintConfig


def test_discovery_prefers_explicit_config(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[tool.termlint.logging]\nlevel = \"WARNING\"\n",
        encoding="utf-8",
    )

    explicit = tmp_path / "explicit.toml"
    explicit.write_text(
        "[tool.termlint.logging]\nlevel = \"INFO\"\n",
        encoding="utf-8",
    )

    config = TermlintConfig.from_discovery(explicit_config=explicit, start_dir=project)
    assert config.logging.level == "INFO"


def test_discovery_uses_nearest_project_pyproject(tmp_path: Path):
    root = tmp_path / "root"
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[tool.termlint.logging]\nlevel = \"DEBUG\"\n",
        encoding="utf-8",
    )

    config = TermlintConfig.from_discovery(start_dir=nested)
    assert config.logging.level == "DEBUG"


def test_discovery_falls_back_to_user_config(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Match TermlintConfig.user_config_candidates():
    # 1) XDG_CONFIG_HOME/termlint/config.toml
    # 2) Path.home()/.config/termlint/config.toml
    # 3) APPDATA/termlint/config.toml
    # 4) Path.home()/.termlint/config.toml
    #
    # The most stable one to control cross-platform is APPDATA.
    appdata = tmp_path / "appdata"
    user_cfg = appdata / "termlint" / "config.toml"
    user_cfg.parent.mkdir(parents=True)
    user_cfg.write_text(
        "[termlint.logging]\nlevel = \"ERROR\"\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("APPDATA", str(appdata))

    config = TermlintConfig.from_discovery(start_dir=workspace)
    assert config.logging.level == "ERROR"


def test_discovery_defaults_when_no_configs(tmp_path: Path):
    config = TermlintConfig.from_discovery(start_dir=tmp_path)
    assert config.logging.level == "WARNING"
    assert config.verifier.source is None
    assert config.pipeline.stages == ["extract", "normalize", "verify", "report"]
    assert config.reports.include == ["verification", "quality_gate", "ontology_update"]
