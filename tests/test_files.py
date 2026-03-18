from pathlib import Path

from chopshop.files import install_preset, resolve_audio_dir, resolve_preset_dir


class TestResolveAudioDir:
    def test_creates_directory(self, tmp_path):
        dest = resolve_audio_dir("mybreak", str(tmp_path))
        assert dest.exists()
        assert dest == tmp_path / "mybreak"

    def test_nested_creation(self, tmp_path):
        base = tmp_path / "deep" / "path"
        dest = resolve_audio_dir("break", str(base))
        assert dest.exists()
        assert dest == base / "break"


class TestInstallPreset:
    def test_writes_preset(self, tmp_path):
        content = b"<?xml version='1.0'?><plist><dict></dict></plist>"
        path = install_preset(content, "test_preset", str(tmp_path))
        assert path.exists()
        assert path.read_bytes() == content
        assert path.name == "test_preset.aupreset"

    def test_no_overwrite(self, tmp_path):
        content = b"original"
        path1 = install_preset(content, "mypreset", str(tmp_path))
        path2 = install_preset(b"second", "mypreset", str(tmp_path))
        assert path1 != path2
        assert path1.read_bytes() == b"original"
        assert path2.read_bytes() == b"second"
        assert "mypreset_1.aupreset" in path2.name
