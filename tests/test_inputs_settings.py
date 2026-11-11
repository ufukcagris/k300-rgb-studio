import json

from k300fx import inputs, layouts, settings


def test_altgr_fake_left_ctrl_is_dropped_but_real_ctrl_is_kept():
    fake = [(0x1D, False, 0, 1.0000), (0x38, True, 0, 1.0004), (0x10, False, 0, 1.2)]
    assert [e[0] for e in inputs.drop_fake_ctrl(fake)] == [0x38, 0x10]        # sahte Ctrl atildi
    real = [(0x1D, False, 0, 1.0), (0x10, False, 0, 1.3)]                     # Ctrl+Q
    assert inputs.drop_fake_ctrl(real) == real
    slow = [(0x1D, False, 0, 1.0), (0x38, True, 0, 1.5)]                      # Ctrl basili, sonra AltGr
    assert len(inputs.drop_fake_ctrl(slow)) == 2


def test_fn_report_is_recognised_only_for_the_observed_press_code():
    down = list(bytes.fromhex("ff00010c") + bytes(60))        # Fn basildi (gozlenen rapor)
    up = list(bytes.fromhex("ff000000") + bytes(60))          # birakildi
    assert inputs.is_fn_report(down) and not inputs.is_fn_report(up)
    assert not inputs.is_fn_report([]) and not inputs.is_fn_report(None)
    assert not inputs.is_fn_report([0xF0, 0x0C, 0x02, 0x03])  # mod secim yaniti Fn degildir


def test_fn_press_reaches_the_effects_as_the_fn_key():
    import time
    for name in layouts.LAYOUT_NAMES:
        kl = inputs.KeyListener()
        kl.layout = name
        kl._q.append((0, False, layouts.VK_FN, time.time() - 0.5))
        events = kl.poll()
        assert events and layouts.keys(name)[events[0][0]].label == "Fn"
        assert 0.5 < events[0][1] < 0.8                       # Fn, bosluk cubugunun sagindaki alt satirda


def test_only_the_fake_left_shift_is_filtered_not_the_real_right_shift():
    assert inputs.is_fake_shift(0x2A, True)           # Windows'un uydurdugu E0 2A
    assert not inputs.is_fake_shift(0x2A, False)      # gercek sol Shift
    assert not inputs.is_fake_shift(0x36, True)       # sag Shift genisletilmis gelse bile GERCEK
    assert not inputs.is_fake_shift(0x36, False)


def test_zone_mapping_stays_near_edges():
    assert -0.5 <= inputs.x_to_zone(0.0) <= 0
    assert 4 <= inputs.x_to_zone(1.0) <= 4.5


def test_settings_migration_from_old_unversioned_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    (tmp_path / "K300FX").mkdir()
    (tmp_path / "K300FX" / "settings.json").write_text(json.dumps(
        {"effect": "Nefes", "fps": 30, "send_fps": 25, "params": {"Nefes": {"speed": 3}}}), encoding="utf-8")
    data = settings.load()
    assert data["effect"] == "Nefes"                       # kullanici secimi korunur
    assert "fps" not in data and "send_fps" not in data    # artik sabit
    assert data["params"] == {}                            # eski ayar semasi uyumsuz, temizlenir
    assert data["version"] == settings.DEFAULTS["version"]
    assert data["layout"] == "tr" and data["language"] == "auto"


def test_typing_heat_setting_is_reset_when_its_meaning_changed(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    (tmp_path / "K300FX").mkdir()
    (tmp_path / "K300FX" / "settings.json").write_text(json.dumps(
        {"version": 7, "params": {"Yazma hızı ısısı": {"speed": 1.0}, "Akış": {"theme": "Neon"}}}), encoding="utf-8")
    data = settings.load()
    assert "Yazma hızı ısısı" not in data["params"]        # eski 1.0 artik "1 tus/sn" olurdu
    assert data["params"]["Akış"]["theme"] == "Neon"       # digerleri korunur


def test_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    data = settings.load()
    data["brightness"] = 0.4
    data["layout"] = "us"
    data["params"] = {"Akış": {"theme": "Neon"}}
    settings.save(data)
    again = settings.load()
    assert again["brightness"] == 0.4 and again["layout"] == "us"
    assert again["params"] == {"Akış": {"theme": "Neon"}}


def test_settings_survive_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    (tmp_path / "K300FX").mkdir()
    (tmp_path / "K300FX" / "settings.json").write_text("{bozuk json", encoding="utf-8")
    assert settings.load()["effect"] == settings.DEFAULTS["effect"]
