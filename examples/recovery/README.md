# Recovery: what happens when an agent dies mid-task

| What died | Who handles it | How |
|---|---|---|
| a **workflow's** own agent | the platform | **resume**: the code runs again, but calls it already made return their recorded results and `task.now()` its recorded time. `task.guard(...)` raises `StateChanged` if the world moved meanwhile |
| a **step** inside a workflow | the workflow's code | the call raises **`AgentLost`** (`started`, `last_progress`, `effects`); `task.retry(...)` and `task.hold(...)` cover the usual answers |
| a task called from a **script or the UI** | the caller | the task ends **LOST**; `call` raises `AgentLost`, the UI offers Retry |

The server re-runs nothing on its own, except a task that never started (it is redelivered).

| File | Shows |
|---|---|
| `declare_analysis.py` | `effects=`: `count_cells` is `NONE`; `segment` makes no claim, because it stores a new dataset |
| `declare_robot.py` | `App(effects=Effects.IRREVERSIBLE)` as the app's default, and an `@app.state` plate to guard on |
| `workflow.py` | `@app.workflow`, `task.retry`, handling `AgentLost`, `task.hold(lost=...)`, `task.guard` / `StateChanged` |
| `call_directly.py` | a script deciding about a lost task: `retry`, and `AgentLost.started` |

Images cross between apps as **mikro structures** (a `SingleChannelImage` lens): each app
fetches the pixels from mikro itself. Values held in one agent's memory, and paths on one
machine, don't cross.

## `effects=`: what running an action again would do

| `Effects` | running it again… | e.g. |
|---|---|---|
| `NONE` | changes nothing | count cells, read absorbance |
| `REPEATABLE` | leaves the same state as running it once | set a dataset's name |
| `UNKNOWN` (no claim) | nobody has said | store a new label dataset |
| `IRREVERSIBLE` | happens again, in the real world | dispense liquid |

It is **information, never a rule**: a workflow reads it off `AgentLost.effects`, a person
sees it on a hold or in the UI. On an app, `effects=` is the default for the actions that
make no claim of their own; an action's own claim wins.

## `@app.workflow`: an action that may call others, and is resumed

- **Only a workflow may call other actions.** Registering a plain action that depends on
  another app's actions is refused, and a plain action's call raises `NotAWorkflowError`.
- **Finished work is never redone.** A resumed workflow gets each finished call's result back,
  whatever that call's effects: the segmentation that already stored its dataset is not run again.
- **In exchange, the code must be deterministic.** Outside values come in only through calls
  and `task` (`task.now()`, `task.random()`, `task.sleep()`, `task.record(fn)`), because those
  are what gets recorded. A run that takes another path raises `NonDeterministicWorkflow`.
- **Resumed only by the code it ran**, and only so often (three times): a changed workflow, or
  an agent that dies every time, ends the task LOST instead.

## `AgentLost`: a step's death is an exception

```python
try:
    handler.dispense(well, volume_ul=v)
except AgentLost as lost:
    if not lost.started:        # never reached the robot: nothing happened
        handler.dispense(well, volume_ul=v)
    else:                       # started, fate unknown: a person decides
        task.hold(f"dispense into {well} was lost: check the well", lost=lost)
```

- `task.retry(call, *args, attempts=3)` tries again only a step that never started;
  `if_started=True` is you saying a repeat is fine. Other exceptions are never retried.
- `task.hold(message, lost=...)` pauses the workflow with your message, and the lost step's
  effects and progress, until a person resumes it (it carries on after the hold) or cancels it.
  A hold that was resumed is recorded: a resumed workflow does not hold there again.

## `task.guard(state, *paths)`: the world may change while you are down

```python
with task.guard(handler.plate, "barcode"):
    handler.dispense(well, volume_ul=v)
```

It records the revision of the robot's `plate` state. On resume, the block raises `StateChanged`
if the barcode changed by anything other than this workflow's own calls, or the robot
restarted. A guard sees only what an app models as state, so the robot publishes its plate.

## Failure scenarios

All of these are `stain_and_measure` (`workflow.py`) unless a scenario says otherwise.

- **The workflow's agent dies after segmentation.** On restart it resumes: `count_cells` and
  `segment` return their recorded results, `task.now()` its recorded time, and it goes on at
  `dispense`.
- **`count_cells`' agent dies.** `task.retry(..., if_started=True)` counts again.
- **`segment`'s agent dies after starting.** The workflow logs it and goes on without labels:
  its choice, in its code.
- **The robot is offline when the dispense is sent.** `AgentLost(started=False)`: nothing was
  dispensed, and it is sent again.
- **The robot dies mid-dispense.** The workflow holds with the lost step's details; a person
  checks the well and resumes or abandons.
- **The plate is swapped while the workflow is held, and the workflow's agent dies too.** The
  resumed run enters the guard again and raises `StateChanged`.
- **A script dispenses directly** (`call_directly.py`): `call` raises `AgentLost`, and the
  script decides.
- **The UI goes away.** Nothing happens to the task; a *caller* disconnecting is not a failure.
