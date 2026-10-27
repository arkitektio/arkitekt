# Bloks

A blok is a panel an app brings with it: a tree of components the user interface
draws, which reads the app's [state](state.md) and whose buttons call its actions.
Bloks are written in BSX, blok language v2, which reads like JSX:

```python
app.blok(
    "monitor",
    """
    <Html>
      <Card>
        <CardHeader><CardTitle>Stage</CardTitle></CardHeader>
        <CardContent>
          <Text>{self.Stage.x_um} µm</Text>
          <Button onClick={self.home() into homing} disabled={homing.running}>Home</Button>
        </CardContent>
      </Card>
    </Html>
    """,
)
```

The root names what the blok is: `<Html>` for a panel (see [Contexts](#contexts)).

`arkitekt create my-analyst --template blok` writes a whole app around one.

A blok is checked here, when it is declared, by the spec's validator: the same rules the
server and the renderer hold it to. An error raises a `BlokError` (a `ValueError`) with a
stable code, such as `roots.unknown` or `callback.unbound`; a warning is a `CatalogWarning`
with its code. It is sent as its BSX source, which the server parses into the same tree.

## The language in short

- `attr="..."` is always a literal string. `attr={...}` is an expression: numbers and
  booleans are expressions too (`min={1}`, `fullWidth={true}`). As in JSX, `attr="outline"`
  is shorthand for `attr={"outline"}`; both store the same literal. A quoted value is
  always a string, so `disabled="true"` is refused for a BOOL prop (`props.literal_type`).
- Text children fill the component's text prop: `<Button>Home</Button>`,
  `<Text>Arrived at {move.args.position}</Text>`.
- Only components with a text prop take text. Containers such as `div`, `Card` or
  `CardContent` do not: `<div>hello <div>…</div></div>` is refused with
  `bsx.text_not_accepted`. Wrap the text instead:
  `<div><p>hello</p><div>…</div></div>`. This follows React Native, where a `div` is a
  View and only `p` / `span` (Text) hold text, so the same blok renders on both. Inside a
  component that does take text, text mixed with elements is fine
  (`<p>hello <span>world</span></p>`): the loose text becomes `span` nodes inside `html@1`
  components and `Text` nodes everywhere else, so an html-only blok needs no `ui@1`.
- Expressions are a small JavaScript subset: paths, JSON literals, calls with named
  arguments (`fmt.number(value: x, digits: 1)`), `== != > >= < <=`, `&& || !`, `a ?? b`
  and `c ? a : b`. Functions live in namespaces (`cmp logic math str list obj val fmt time`).
- `a ?? b` is the first of its operands that is not null (`logic.coalesce`; a chain
  `a ?? b ?? c` is one call). It binds looser than `||` and `&&` (`a || b ?? c` is
  `(a || b) ?? c`) and tighter than the ternary. `?.` is not part of the language.
- Conditional classes: `className={["px-2", run.running && "animate-pulse"]}`.
- `<if when={...}>` with `<else when={...}>` / `<else>`; `when={...}` on any component;
  `<foreach items={...} let="p" key={p.id}>`; `<suspense>` with `<fallback>` and `<error>`.
- A foreach's `key` is optional: without one, items are keyed by their position. That is
  right for scalars (`<foreach items={self.Analysis.histogram} let="bin">`); a list of
  objects should be keyed by a stable field, and without a key it warns
  `foreach.position_key`.
- Colours are theme roles (`bg-muted`, `text-success`, `border-info/30`), never palette
  colours or hex values: the validator warns about `bg-green-500` and names the role.
- The spectral roles `spectrum-violet`, `-blue`, `-cyan`, `-green`, `-yellow`, `-orange`
  and `-red` (each with `-soft`) are fixed hues for wavelengths and channels: Tailwind
  classes (`bg-spectrum-green-soft`), scene colours and logo pens. Their chroma follows the
  brand's, like the status roles. The bands (nm, lower bound included) are violet 380–450,
  blue 450–490, cyan 490–520, green 520–565, yellow 565–590, orange 590–625 and red
  625–750; below 380 is violet, from 750 red.

### `html@1` and what it means on React Native

`html@1` holds exactly three tags, chosen because each has one direct React Native
equivalent. The web is the reference rendering; pokket (React Native) draws the same
blok to match it:

| Tag | Web | React Native (pokket) | What that implies |
|---|---|---|---|
| `div` | `<div>`, a block | `<View>` | A box for layout: padding, borders, background, `flex`/`gap` classes. It never holds text, only elements. Children stack; a run of inline children (`span`, `a`, …) flows on one line, on both. |
| `p` | `<p>` | `<Text>`, a block of its own | A paragraph: starts on its own line, wraps, and holds text, `{…}` and `span`s. Put only `span`s inside it, never a `div`: React Native cannot lay out a View inside Text reliably. |
| `span` | `<span>` | `<Text>` nested in a `<Text>` | An inline run: it flows with the text around it and inherits its font, size and colour, overriding only what it sets. Consecutive `span`s in a `div` share one line. |

What you opt into:
- **Text classes on a `div` reach the text inside it**, as CSS inheritance does on the web
  (pokket passes a `div`'s `text-*`, `font-*`, `italic`, `leading-*`, … down to its texts).
  What a `p`/`span` sets itself wins: they default to `tone="default"`, `size="sm"`,
  `weight="normal"`, so colour, size and weight belong on the `p`/`span`, not the `div`.
- **Layout is flexbox or block.** No floats, no `grid` on a `div` (use `ui@1`'s `Grid`).
  React Native has only flexbox: a `View` is always a flex column, so `gap-*`/`grow` take
  effect there even without `flex`, while the web ignores them on a plain block. Write
  `flex flex-col gap-*` whenever you space children, and both look the same.
- **No other raw tags.** Headings, lists, tables, links and images come from `ui@1`
  (`Heading`, `Table`, `Link`, `Image`, …), which render natively on both.

### What an agent's blok reads

| Root | What it is |
|---|---|
| `self.<state>.<field>` | The agent's own state. |
| `self.tasks.<action>` | The latest task of one of its actions. |
| `self.assets.<name>` | An asset it registered (`app.register_asset`). |
| `args.<key>` | The item the blok is opened for (`args=`). |
| a bare local | Its form state (`locals=`). |
| a name given with `into` | The task record of that one call. |
| `queries.<name>` / `subscriptions.<name>` | Its declared reads (`queries=`, `subscriptions=`). |
| `viewer`, `then` | Who is looking; the moment being viewed while time-travelling (null while live). |

What it reads and calls of `self` becomes its one dependency when the agent is built:
a state or action the app does not declare is refused there.

### Time

Nothing ticks in an expression: `then` is null while the viewer is live and the ISO
timestamp of the moment they are looking at while they travel back. A query that should
follow the viewer through time passes it as an ordinary variable (`variables={"at": "then"}`).
Relative times and countdowns are a component that ticks by itself:
`<Time value={self.Stage.moved_at} relative />` ("3 minutes ago"), or
`<Time value={self.Stage.moved_at} format="HH:mm" />`. `time.diff(start: a, end: b)` is the
seconds between two timestamps and `fmt.duration(seconds: s)` writes them out.

### Callbacks do one thing

A callback holds exactly one task call or one effect: `queries.<name>.refetch()`,
`queries.<name>.fetch_more(after: ...)` (of a query that declares `more`), `task.answer(...)`
or `ui.copy(text)`.
A task call names every argument: `onClick={self.move_to(position: p.id) into move}`.
Derive state from the call's record instead of keeping your own:
`variant={move.args.position == p.id ? "default" : "outline"}`. A task record has `status`,
`running`, `done`, `failed`, `progress`, `message`, `error`, `args`, `ask`, `answer` and
`returns.<port>`. Reading an unnamed return (`returns.return0`) warns `returns.unnamed`. Notifications are declarative: `<Toast task={move}><done>...</done></Toast>`.

### Named returns

A return is read by its key, so name the ones a blok reads. There are two spellings:

```python
from typing import Annotated, NamedTuple
from arkitekt import Key

@app.action
def count_cells(image: Image) -> Annotated[int, Key("count")]:
    """Count the cells"""
    ...

class Measured(NamedTuple):
    count: int
    mean: float

@app.action
def measure(image: Image) -> Measured:
    """One return per field: `count` and `mean`"""
    return Measured(count=12, mean=0.4)
```

A blok then reads `counted.returns.count` and `measured.returns.mean`. `Key` also names one
element of a `tuple[...]` return; the others stay `return<N>`. A returned (or yielded)
`NamedTuple` is unpacked into the ports its fields name. A return without a key stays
`return0`, and so does its hash: a numpy docstring's return name is only the port's label,
never its key. `Key` names a return only; an argument is keyed by its parameter name.

## Locals, queries and the demo

```python
from arkitekt import Local, Query

app.blok(
    "deconvolver",
    """
    <Html>
      <Card>
        <Slider bind={iterations} min={1} max={100} />
        <Input bind={name} />
        <Button onClick={self.deconvolve(image: args.image, iterations: iterations, name: name) into run}>Run</Button>
        <foreach items={queries.positions.value} let="p" key={p.id}><Text>{p.name}</Text></foreach>
      </Card>
    </Html>
    """,
    args={"image": Image},
    locals={
        # The argument's port (an INT, its label, its default), remembered on this device.
        "iterations": Local.like(deconvolve, "iterations", persist=True),
        # Nothing said: the argument it is passed to whole gives its kind.
        "name": Local(),
    },
    queries={
        "positions": Query(
            service="mikro",
            document="query($image: ID!) { positions(image: $image) { id name } }",
            variables={"image": "args.image.id"},
        ),
    },
    demo={"args": {"image": {"id": "1"}}},
)
```

- `locals`: form state that feeds a call, written only through `bind` on a control and
  read bare. A local is a port, and its kind is usually told by the blok, so `Local()` is
  enough. In order, the first of these that tells wins:
  1. a type: `Local[float]()`, `Local[Image | None]()`, `Local(type=list[str])`;
  2. an action's argument: `Local.like(deconvolve, "iterations")` copies that argument's
     port (kind, identifier, children, choices, units, widget, label, description) and
     its default unless you pass one; register the action first;
  3. the default: `Local(15)` is an INT, `Local(["a"])` a list of strings (`None`, `[]`,
     `{}` tell nothing);
  4. a call it is passed to whole: `self.deconvolve(image: image)` gives `image` the
     argument's port;
  5. the control bound to it whole: `<Switch bind={on} />` makes a BOOL, an `Input` a
     STRING, a `Slider` a FLOAT (list and dict controls tell too little);
  6. else it is ANY: an untyped value, checked against nothing, with no error.

  What the local says itself (`persist`, `description`, a default) is kept over what is
  inferred. A bound control must write the local's kind, and a call argument built from it
  must fit the action's port. `persist=True` remembers the last input on this device. A
  bare value is a local with that default.
- `queries` / `subscriptions`: declared GraphQL reads on a service, never a mutation. A
  query is checked against its service's schema when the app knows it. `Query(more="cells")`
  names the list field new pages append to, which `queries.<name>.fetch_more(...)` needs.
  While the viewer travels in time a subscription pauses and shows its `history` query.
- `demo`: what a preview renders it with, mirroring the roots (`deps`, `args`, `task`,
  `queries`, `subscriptions`). Placeholders for the states it reads when left out.
- `catalogs`: the catalogs it needs (`"ui@1"`, `"scene@1"`); those its components come
  from when left out.
- `module`: the module (an app's own unversioned extras) it renders against besides its
  catalogs; the Orkestrator's when left out. A name that is neither the Orkestrator's nor
  one this app declared warns `module.unknown`.

A custom blok (`rekuest.createBlok`) declares every dependency it reads: each `deps.<key>`
names one of its declared dependencies, with the demands it needs. A dependency no agent is bound to reads as `failed` (code `deps.unbound`), and a call to it
is disabled.

## Contexts

A blok's root names its context, what draws it; there is no `context=` to pass:

| Root | Context | What it is |
|---|---|---|
| `<Html>` | `HTML` | A panel. |
| `<Scene>` | `SCENE` | A 3D view, of models the app brings. |
| `<AgentLogo>` | `LOGO` | The app's logo, drawn with SVG shapes. |
| `<ActionLogo>` | `ACTION_LOGO` | An action's logo, drawn against the action's `task`. |
| `<Overlay>` | `OVERLAY` | Drawn into the space that hosts a run: an action's own blok only. |

Any other root is refused (`context.root_unknown`).

An app has at most one default blok per context (`default=True`): its panel, its scene
and its logo, which a client shows for the app without being told which.

### Logos

The shapes are the SVG elements, capitalised, with camelCase props: `Path`, `Circle`,
`Ellipse`, `Rect`, `Line`, `Polyline`, `Polygon`, `SvgText`, `G`, and `Defs`,
`LinearGradient`, `RadialGradient`, `Stop` and `ClipPath`, which shapes reference as
`url(#id)` by their `id`. A logo paints with the theme's **pens** only:

| Pen | Drawn as |
|---|---|
| `ink` | the text colour |
| `muted` | the muted text colour |
| `brand` / `brand-strong` / `brand-soft` | the viewer's brand hue: plain, with more contrast, faint |
| `surface` | the card behind the logo |
| `success` / `warning` / `info` | the status roles |
| `none` | nothing |

`fill`, `stroke` and a gradient `Stop`'s `stopColor` take a pen or a `url(#id)`. The pens
are the viewer's: they follow their brand, a scene's tint and dark mode, so the actions of
every app look like one set.

An action logo (`@app.action(logo="crop_action_logo")`, or a tree of the action's own)
reads one thing, `task`: the task the viewer last ran of the action. It is null until they
run it. It reads no state and calls no action.

```python
app.blok(
    "crop_action_logo",
    """
    <ActionLogo viewBox="0 0 24 24">
      <Rect x="6" y="6" width="12" height="12" fill="none" stroke="brand-strong" strokeDasharray="2 1" animate="march" />
      <Path d="M6 2v16h16" fill="none" stroke="ink" strokeWidth="2" />
      <Circle cx="12" cy="12" r="2.5" fill={task.running ? "brand" : "muted"} animate="pulse" />
    </ActionLogo>
    """,
)
```

Any shape may `animate`: `spin`, `pulse`, `float`, `draw`, `march` or `blink`, with
`animateDelay` in seconds. A logo has at most 200 components, nests at most 12 deep and
holds at most 16 KB of path data; `app.blok(...)` refuses a bigger one, and so does the
server.

### Logos from SVG files

`from_svg` turns an `.svg` file into the BSX of a logo, rooted at `<AgentLogo>` (or
`<ActionLogo>` with `context="action_logo"`), painting every colour with the nearest pen
(`palette={"#0f172a": "ink", ...}` picks one yourself):

```python
from pathlib import Path
from arkitekt import from_svg

app.blok("crop_logo", from_svg(Path("crop.svg")), default=True)
app.blok("crop_action_logo", from_svg(Path("crop.svg"), context="action_logo"))
```

## An action's own bloks

An action or workflow can bring bloks of its own, one per context, sent with its
definition and named by their root: `<Html>` for a task panel, `<Scene>` for a 3D view,
`<Overlay>` drawn into the space that hosts the run. They read the run as `task`, its args as `args`, the agent running it
as `self` and the agents the run got as `deps.<key>`, the action's dependency keys:

```python
from arkitekt import ActionBlok, Local

@app.workflow(
    bloks=[
        ActionBlok(
            """
            <Overlay>
              <Anchor dep="robot">
                <Popout open={task.ask != null}><ask /></Popout>
              </Anchor>
              <if when={show_path}><Route through={["robot", "stage"]} progress={task.progress} /></if>
            </Overlay>
            """,
            locals={"show_path": Local(True, persist=True)},
        ),
        "<Html><Card><Progress value={task.progress} /><ask /></Card></Html>",
    ]
)
def move(robot: Arm, stage: Stage, slot: int) -> None: ...
```

`bloks=` takes one blok or a list, each a bare BSX string (or parsed tree) or an
`ActionBlok`, which adds `locals`, `demo`, `queries`, `subscriptions`, `catalogs`,
`module` and `description`, like `app.blok`. One blok needs no list:
`@app.action(bloks="<Html>...</Html>")`. Two bloks with the same root are refused.

## What a blok may be made of

The components and their props are written down in **catalogs**, and a blok is checked
against them where it is declared: a component no catalog in force has, a prop it does not
take, or children where none are drawn is reported with its place in the tree.

- **base**: the language (`if`, `else`, `foreach`, `match`, `suspense`, `ask`, ...) and
  every function; every renderer implements it.
- **The standard catalogs**, versioned and owned by the spec: `ui@1`, `scene@1`, `logo@1`,
  `structure@1` and `html@1` (only `div`, `p`, `span`); `STANDARD_CATALOGS` names them.
- **Modules**: an app's own unversioned extras, registered by the UI that draws them.
  The `orkestrator` module (`orkestrator_module()`) is what only the Orkestrator draws
  beyond the catalogs (the further shadcn families, `Chart`, ...). A blok naming no module
  renders against base, the standard catalogs and the Orkestrator's module.

```python
from arkitekt import default_view

view = default_view()
sorted(view.components)               # Accordion, Alert, Badge, Button, Card, ...
view.component("Slider").props        # bind, min, max, step, onChange, ...
```

A catalog finding is a warning by default, since the client's copy may lag the renderer;
`mode="strict"` refuses the blok on the first one.

### Another module

A blok for another renderer names its module, and is checked against base, the standard
catalogs and the components that module declares. A module may define a name a standard
catalog also defines (its own `Slider`): the module's definition is used, and a tree that
uses it warns `catalog.shadow` once per name. Base is never shadowed; a module may not
redefine a base name.

```python
app.ui_catalog("electron", components=[ComponentSpec(name="Gauge", props=(...))])
app.blok("dial", "<Html><Gauge /></Html>", module="electron")
```

One it only names (`module="somewhere-else"`) warns `module.unknown`: no component is
reported unknown here, and the server says what it finds when the app registers (it warns
`module.unknown` too when nobody registered the module in the organization).
