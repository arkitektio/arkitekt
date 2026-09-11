# Choosing the Right App Type

Arkitekt Next offers two primary ways to build and deploy applications: **Standalone Apps** and **Plugin Apps**. Choosing the right approach depends on your specific use case, deployment requirements, and how you intend to distribute your work.

## Decision Guide

Use this decision tree to help you choose:

1.  **Do you want to build your own custom GUI (e.g., PyQt, Napari, Web App)?**
    *   ✅ **Yes** $\rightarrow$ Choose **[Standalone App](standalone_app.md)**.
    *   *Reason:* You need full control over the UI framework and the event loop.

2.  **Are you integrating Arkitekt into an existing application (e.g., a microscope control software)?**
    *   ✅ **Yes** $\rightarrow$ Choose **[Standalone App](standalone_app.md)**.
    *   *Reason:* You are adding connectivity to an existing system.

3.  **Are you working in a Jupyter Notebook or writing a quick analysis script?**
    *   ✅ **Yes** $\rightarrow$ Choose **[Standalone App](standalone_app.md)**.
    *   *Reason:* You want immediate execution without a build step.

4.  **Do you need to distribute your app to other users or deploy it to a server/cluster?**
    *   ✅ **Yes** $\rightarrow$ Choose **[Plugin App](plugin_app.md)**.
    *   *Reason:* Plugins are packaged as Docker containers, making them easy to install and run anywhere.

5.  **Does your app require specific system dependencies (non-Python) or a reproducible environment?**
    *   ✅ **Yes** $\rightarrow$ Choose **[Plugin App](plugin_app.md)**.
    *   *Reason:* Docker containers ensure your app runs in the exact environment it needs, regardless of the host system.

---

## Detailed Comparison

### 1. Standalone App (The "Easy" Way)

**Best for:** Custom GUIs, Integration, Scripting, Prototyping, Local Control.

In this mode, your code runs directly in your local Python environment. You are responsible for starting and stopping the script.

*   **Custom GUI Support:** If you are building a desktop application with PyQt, PySide, or integrating into tools like Napari, this is the way to go. You manage the window and the event loop, while Arkitekt runs in the background to handle communication.
*   **Integration:** Perfect for adding Arkitekt connectivity to existing tools. You can start the Arkitekt client as a background thread.
*   **Prototyping:** The fastest way to test an idea. No Dockerfile, no manifest, just `import arkitekt_next`.

**Example Use Cases:**
*   A custom PyQt application for controlling a lab device.
*   A Napari plugin that sends images to Arkitekt for processing.
*   Running a one-off data processing script in Jupyter.

### 2. Plugin App (The "CLI" Way)

**Best for:** Distribution, Production, Reproducibility, Traceability, Server-side Execution.

In this mode, your app is a structured project that gets built into a Docker container. It is managed by the Arkitekt platform.

*   **User Interface (Bloks):** Plugin apps **do not** have their own native GUI windows. Instead, they can hook into Arkitekt's "Blok" system. You define widgets and UI elements that are rendered by the Arkitekt client (web or desktop). This allows your app to provide a UI that feels native to the platform.
*   **Reproducibility & Traceability:** Because your app is containerized (Docker) and versioned, every run is reproducible. Arkitekt tracks exactly which version of your app processed which data, providing full provenance and traceability for scientific workflows.
*   **Execution:** You don't run these apps with `python app.py` in production. Instead, you use the CLI commands:
    *   `arkitekt-next run dev`: Runs the app in development mode (hot-reloading, local connection).
    *   `arkitekt-next run prod`: Runs the app in production mode (simulating the container environment).
    *   *Note:* These commands expect an entrypoint (e.g., `app.py`) and accept parameters like `--url` to connect to specific Arkitekt instances.

**Example Use Cases:**
*   A deep learning inference server (e.g., Segment Anything Model) shared with your lab.
*   A long-running workflow worker that processes data in the background.
*   A tool that requires complex dependencies (e.g., specific CUDA versions, system binaries like `ffmpeg`).

## Summary

| Feature | Standalone App | Plugin App |
| :--- | :--- | :--- |
| **Setup** | Minimal (import library) | Structured (Manifest + Docker) |
| **UI/GUI** | **Full Custom Control** (PyQt, etc.) | **Integrated Bloks** (Rendered by Arkitekt) |
| **Execution** | Manual (`python script.py`) | Managed (`arkitekt-next run dev/prod`) |
| **Environment** | Local Python Env | Docker Container (Reproducible) |
| **Distribution** | Share script | Docker Registry |
| **Traceability** | Limited | **Full Provenance** |
