# Flavours

In Arkitekt Next, **Flavours** allow you to provide multiple build configurations for the same application. This is essential for supporting different hardware environments (like CPU vs. GPU) or deployment scenarios without maintaining separate codebases.

## What is a Flavour?

A flavour is essentially a specific recipe for building your app into a Docker container. It consists of:

1.  **A Dockerfile:** Defines the environment (OS, libraries, Python version).
2.  **Configuration (`config.yaml`):** Metadata about the flavour, including its description and **selectors**.

When you publish your app, you publish all its flavours. When a user (or the Arkitekt platform) installs your app, it automatically selects the best flavour based on the available hardware and resources.

## Why use Flavours?

*   **Hardware Acceleration:** You can have a `vanilla` flavour for standard CPU execution and a `cuda` flavour that includes NVIDIA drivers and PyTorch with CUDA support.
*   **Resource Management:** You might have a `light` flavour for low-memory environments and a `heavy` flavour that loads large models into RAM.
*   **Dependency Variations:** Support different backend libraries or system tools in separate containers.

## Creating a Flavour

You can add a new flavour to your project using the CLI:

```bash
arkitekt plugin flavour add --flavour <name>
```

**Example:** Adding a GPU flavour

```bash
arkitekt plugin flavour add --flavour gpu --description "CUDA enabled build"
```

This will create a new directory in `.arkitekt/flavours/gpu/` containing a `Dockerfile` and `config.yaml`. You can then customize the Dockerfile to include the necessary GPU drivers and libraries.

## Selectors

Selectors declare the hardware/capability requirements a backend must satisfy
to run the flavour. They are stored in the flavour's `config.yaml`, published
with the app image, and evaluated by the deployer that places pods. The
canonical reference (all kinds, fields, units, and the Kubernetes/Compose
mapping) lives in the kabinet server repo: `docs/selectors.md`.

Every selector carries `kind`, `required` (default `true` — a hard
constraint) and `weight` (scores optional selectors, like Kubernetes'
preferred-scheduling weight), plus kind-specific fields:

*   **`cpu`** — `min_count` (cores), `frequency` (MHz), `arch` (`amd64`, `arm64`, ...)
*   **`ram`** — `min` (MB of system memory)
*   **`cuda`** — `compute_capability` (e.g. `"8.6"`), `cuda_version`, `memory` (VRAM MB), `count` (GPUs)
*   **`rocm`** — `api_version`, `api_thing`
*   **`oneapi`** — `oneapi_version`
*   **`label`** — `key`, `value` (matches a backend resource's qualifiers; omit `value` to require only the key)

A service your app needs (mikro, rekuest, ...) is **never** a selector — it is
a requirement in the manifest, composed by the deployment. Selectors only
constrain hardware placement.

### Example `config.yaml`

```yaml
description: "A high-performance GPU build"
selectors:
  - kind: cuda
    compute_capability: "8.6"
    memory: 8000
  - kind: ram
    min: 16000
  - kind: label
    key: microscope
    value: lightsheet
    required: false
    weight: 10
dockerfile: Dockerfile
```

## Building Flavours

When you run `arkitekt build`, the CLI will build the default flavour (usually `vanilla`). To build a specific flavour, use the `--flavour` flag:

```bash
arkitekt build --flavour gpu
```

## Publishing

When you run `arkitekt publish`, you can publish specific builds associated with their flavours. The platform will register these flavours under the same app version, allowing for seamless deployment across diverse infrastructure.
