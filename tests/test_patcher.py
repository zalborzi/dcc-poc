from pipeline import patcher


def test_apply_patches_falls_back_when_jsonpatch_fails(monkeypatch):
    class DummyJsonPatch:
        JsonPatchException = Exception

        @staticmethod
        def apply_patch(*args, **kwargs):
            raise DummyJsonPatch.JsonPatchException("boom")

    monkeypatch.setattr(patcher, "jsonpatch", DummyJsonPatch)

    loire = {}
    patches = [{"op": "add", "path": "/nested/field", "value": "ok"}]

    updated = patcher.apply_patches(loire, patches)

    assert updated != loire
    assert updated["nested"]["field"] == "ok"
    assert loire == {}
