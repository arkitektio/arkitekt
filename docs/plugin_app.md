# Plugin App

Plugin apps are the recommended way to build and distribute Arkitekt applications. They are structured projects that can be built into Docker containers and published to the Arkitekt registry.

## Initialization

To create a new plugin app, use the `arkitekt-next init` command. This will guide you through the setup process and create the necessary files (manifest, entrypoint, etc.).

```bash
arkitekt-next init
```

You will be prompted to enter details about your app, such as:
- **Identifier**: A unique name for your app (e.g., `com.example.myapp`).
- **Version**: The initial version (e.g., `0.0.1`).
- **Template**: A starting template (e.g., `simple`).

This command creates a `arkitekt.yaml` manifest file and a basic project structure.

## Development

You can develop your app by editing the generated python files. The entrypoint is usually `app.py` (or whatever you specified during init).

To run your app locally during development, you can use:

```bash
arkitekt-next run dev
```

This command will:
1. Build the app in development mode.
2. Connect to a local Arkitekt server. (use --url to specify a different server)
3. Enable hot-reloading for easier development.


## Building

Once you are ready to package your app, you can build it into a Docker container using the `arkitekt-next build` command.

```bash
arkitekt-next build
```

This command will:
1. Read your manifest and configuration.
2. Build a Docker image for your app.
3. Tag the image with a build ID.

You can specify a "flavour" if you have multiple build configurations defined.

## Publishing

To share your app with others, you can publish it to a Docker registry (like Docker Hub) using the `arkitekt-next publish` command.

```bash
arkitekt-next publish
```

This command will:
1. Find the latest build.
2. Tag the Docker image with your username and app version.
3. Push the image to the registry.
4. Generate a deployment file.

## Workflow Summary

1. **Init**: `arkitekt-next init` - Create project structure.
2. **Code**: Write your application logic.
3. **Build**: `arkitekt-next build` - Create Docker image.
4. **Publish**: `arkitekt-next publish` - Push to registry.

This workflow ensures your app is versioned, packaged, and ready for deployment on any Arkitekt instance.
