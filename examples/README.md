# Examples

Eleven small, self-contained scripts. Each one declares its own dependencies in a
[PEP 723](https://peps.python.org/pep-0723/) header, so there is nothing to install:

```bash
uv run --script examples/hello.py
```

Every script needs a reachable Arkitekt server. It is taken from `$FAKTS_URL`, or passed
explicitly — `run(app, url="localhost")`, `easy("name", service, url="localhost")`. The first run
opens a browser to authenticate; `headless=True` prints the device code instead.

## Two directions

An app either **offers** actions (`run(app)` — it stays up and others call it) or **calls** other
services (`easy(...)` — it does its thing and exits). Most of these show one or the other.

| Script | Direction | Shows | Needs |
|---|---|---|---|
| `hello.py` | offer | one `@app.action`, and nothing else | — |
| `measure_nuclei.py` | offer | real work inside an action, an `@app.model` result | — |
| `in_memory_pipeline.py` | offer | `app.memory_structure(np.ndarray)`: arrays crossing actions on the agent | — |
| `microscope_stage.py` | offer | `@app.state`, `@app.startup`, `@app.background` | — |
| `typed_context.py` | offer | `App(app_context=Setup)` and `run(app, context=...)` | — |
| `upload_cells3d.py` | call | uploading a z-stack with a pyramid | mikro |
| `denoise_volume.py` | offer | spec ports (`Volume`), an injected `Mikro`, derivation edges | mikro |
| `upload_nifti.py` | call | nibabel, and the `(i,j,k) -> (z,y,x)` reversal | mikro |
| `read_with_bioio.py` | call | bioio as the reader, and dropping padded axes | mikro |
| `upload_trace.py` | call | an array dataset with a unit and a sampling clock | elektro |
| `detect_spikes.py` | offer | spec ports (`SingleChannelTrace`), an injected `Elektro` | elektro |

The mikro and elektro scripts need those services deployed on the server you connect to.

`recovery/` shows what happens when an agent dies mid-task: workflows that resume, `AgentLost`,
`task.retry`/`hold`/`guard`, and what an action's `effects=` tells whoever decides.
