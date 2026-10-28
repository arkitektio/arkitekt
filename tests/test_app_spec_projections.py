"""An app is declared once; the login manifest, the build record and the
inspection are views of that one declaration."""

from arkitekt_spec import AppManifest

from arkitekt import App
from arkitekt.app.spec import app_declaration, app_inspection, app_manifest


def _app() -> App[None]:
    app = App("com.x", "1.2.3", author="me", description="What it is", scopes=["read"])

    @app.action
    def double(x: int) -> int:
        """Double

        Doubles a number
        """
        return x * 2

    return app


def test_the_login_manifest_is_the_spec_manifest_of_the_app() -> None:
    """What an app logs in as is its spec identity, field for field."""
    app = _app()
    login = app.manifest
    assert isinstance(login, AppManifest)
    for field in ("identifier", "version", "author", "description", "scopes"):
        assert getattr(login, field) == getattr(app_manifest(app), field)


def test_the_inspection_is_the_declaration_seen_by_a_build() -> None:
    """The inspection is a projection of the declaration, not a second assembly."""
    app = _app()
    run = app.snapshot()
    declaration = app_declaration(app, run)

    assert app_inspection(app, run) == declaration.to_inspection()
    assert [i.definition.key for i in declaration.implementations] == ["double"]
    assert declaration.manifest.description == "What it is"


def test_the_build_records_the_scopes_a_run_asks_for() -> None:
    """A mandate key is pinned to what the build records: a run with its provider asks for no more."""
    from rekuest.arkitekt import rekuest_provider, rekuest_service

    app = _app()
    run = app.snapshot(provider=rekuest_provider)
    declaration = app_declaration(app, run)

    assert declaration.manifest.scopes == run.manifest.scopes
    assert set(rekuest_service.get_scopes()) <= set(declaration.manifest.scopes)
