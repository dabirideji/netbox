from pathlib import Path

from netbox.crypto import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "netbox.sqlite3"
    db_path.write_text("")

    encrypted = encrypt_secret(db_path, "re_123456789")
    assert encrypted
    assert encrypted != "re_123456789"
    assert decrypt_secret(db_path, encrypted) == "re_123456789"
