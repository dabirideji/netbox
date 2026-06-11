from netbox.util.paths import project_root


def test_project_root_points_at_repository() -> None:
    root = project_root()
    assert (root / "backend" / "src" / "netbox").is_dir()
    assert (root / "config" / "backend.json").is_file()
