# Standalone App

The standalone app is the easiest way to get started with Arkitekt. It is a
Python script that connects to an Arkitekt instance and offers functionality —
good for development, testing and simple scripts.

## Offering actions

Declare an `App`, register functions on it, and `run` it. `run` connects, offers
the registered functions, and blocks until you stop it.

```python
from arkitekt import App, run

app = App("my.app")

@app.action
def my_function() -> str:
    """Say hello."""
    return "Hello from my standalone app!"

if __name__ == "__main__":
    run(app)   # offers `my_function` until interrupted
```

## Calling other apps

`easy` is the other direction: it declares an app from the *services* you name
and hands you their clients. Nothing connects until it is entered, and what you
get back is the clients — one service gives you one client, several give you a
tuple.

```python
from arkitekt import easy
from mikro import mikro_service

with easy("my.app", mikro_service) as mikro:
    dataset = mikro.get_array_dataset("some-id")
```

## Configuration

Both take the same keyword arguments:

- `version` — the app's version (default `"0.0.1"`).
- `url` — the fakts server. Defaults to `$FAKTS_URL`, then the public
  deployment at `https://go.arkitekt.live`.
- `scopes` — the scopes the app requests (default `["openid"]`).
- `author`, `logo` — shown in the UI.
- `redeem_token` — a token to provision a new app with.
- `token` — a previously issued credential, `client_id:refresh_token`.
- `headless` — print the device-code prompt instead of opening a browser.
- `skip_cache` — neither read nor write the fakts cache: log in, and keep the
  session in memory only.
- `reauth` — log in again even when a session is cached, and cache the new one.
  Defaults to `$ARKITEKT_REAUTH`.
- `force` — take over an existing agent connection of this app.
- `allow_insecure_transport` — talk plain http to a server that is not on this
  machine. Off, such a server is refused.

A program with a life of its own (a GUI, a control program) does not call `run`,
which blocks: it calls `run_detached(app, ...)` with the same arguments. See
[Embedding an app](embedding.md).

The identifier defaults to the calling file's name, so `easy()` with no
arguments works for a quick script.

## Limitations

Standalone apps are great for development but have some limitations:

- **No Building**: You cannot build a standalone app into a Docker container using the Arkitekt CLI.
- **No Publishing**: You cannot publish a standalone app to the Arkitekt registry using the Arkitekt CLI.
- **Manual Execution**: You need to run the script manually (e.g., `python my_app.py`).

If you need to distribute your app or run it in a production environment, consider creating a [Plugin App](plugin_app.md).
