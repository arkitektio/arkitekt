# Standalone App

The standalone app is the easiest way to get started with Arkitekt. It allows you to write a python script that connects to an Arkitekt instance and provides functionality. This is great for development, testing, and simple scripts.

## Getting Started

To create a standalone app, you can use the `easy` builder from `arkitekt_next`.

```python
from arkitekt_next import easy

@register
def my_function():
    return "Hello from my standalone app!"

# This will connect to the default Arkitekt instance at localhost:8000
# and register the app with the identifier "my.app"
with easy("my.app", version="0.0.1") as app:
    print("App is running")
    app.run() # registered functions will be available during this call
    print("App has stopped")
```

## Configuration

The `easy` builder accepts several parameters to configure your app:

- `identifier`: The unique identifier for your app (e.g., "com.example.myapp").
- `version`: The version of your app (default: "0.0.1").
- `url`: The URL of the Arkitekt instance (default: "http://localhost:8000").
- `redeem_token`: A redeem-token to authenticate with the Arkitekt instance (optional).
- `headless`: If True, runs in headless mode (default: False).

## Limitations

Standalone apps are great for development but have some limitations:

- **No Building**: You cannot build a standalone app into a Docker container using the Arkitekt CLI.
- **No Publishing**: You cannot publish a standalone app to the Arkitekt registry using the Arkitekt CLI.
- **Manual Execution**: You need to run the script manually (e.g., `python my_app.py`).

If you need to distribute your app or run it in a production environment, consider creating a [Plugin App](plugin_app.md).
