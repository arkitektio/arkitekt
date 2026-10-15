# Bloks

A blok is a panel an app brings with it: a tree of components the user interface
draws, which reads the app's [state](state.md) and whose buttons call its actions.

```python
app.blok(
    "monitor",
    bsx("""
        <Card>
            <CardHeader><CardTitle text="Stage" /></CardHeader>
            <CardContent>
                <span text="@self.Stage.x_um" />
                <Button label="Home" onClick="@self.home().into(homing)" disabled="@homing.running" />
            </CardContent>
        </Card>
    """),
)
```

`arkitekt create my-analyst --template blok` writes a whole app around one.

A blok written as BSX is checked here, as its tree, and sent as the BSX itself: a third of
the bytes of its tree, which the server parses into the same tree. A blok given as a tree
(`bsx(...)`) is sent as one.

## Contexts

A blok's `context` says what draws its root:

| `context` | Root | What it is |
|---|---|---|
| `"html"` (the default) | anything | A panel. |
| `"scene"` | one `<Scene>` | A 3D view, of models the app brings. |
| `"logo"` | one `<SVG>` | The app's logo, drawn with SVG shapes. |

An app has at most one default blok per context (`default=True`): its panel, its scene
and its logo, which a client shows for the app without being told which.

```python
app.blok(
    "logo",
    bsx("""
        <SVG viewBox="0 0 24 24">
            <Defs>
                <LinearGradient id="sky" x2="1">
                    <Stop offset="0" stopColor="#0af" />
                    <Stop offset="1" stopColor="#a0f" />
                </LinearGradient>
            </Defs>
            <Circle cx="12" cy="12" r="11" fill="url(#sky)" />
            <Path d="M6 16 L12 6 L18 16 Z" fill="none" stroke="white" strokeWidth="1.5" />
        </SVG>
    """),
    context="logo",
    default=True,
)
```

The shapes are the SVG elements, capitalised, with camelCase props: `Path`, `Circle`,
`Ellipse`, `Rect`, `Line`, `Polyline`, `Polygon`, `SvgText` (`Text` is the typography
component), `G`, and `Defs`, `LinearGradient`, `RadialGradient`, `Stop` and `ClipPath`,
which shapes reference as `url(#id)` by their `id`. They only go inside an `<SVG>`;
any html blok may draw one too.

An action can be drawn by a logo too: name a logo blok the app declares, or give it a
drawing of its own, which is declared as the logo blok `<action>.logo`. An action without
one is drawn by the app's default logo.

```python
@app.action(logo="logo")
def crop_to_annotation(...): ...

@app.action(logo=bsx('<SVG viewBox="0 0 24 24"><Path d="M4 4h16v16H4Z" fill="#fbbf24" /></SVG>'))
def measure(...): ...
```

A logo is an icon. It has at most 200 components, nests at most 12 deep, holds at most
16 KB of path data (`d` and `points`), and a `foreach` in it draws at most 64 items of its
demo state; `app.blok(...)` refuses a bigger one, and so does the server.

A logo may bind state like any blok, but a client draws it against its `demo_state`
only, never the agent's live state, and runs none of its actions: it is the same
picture every time, and Orkestrator keeps the one it drew. `foreach`, `if` and
`Fragment` take the context they are placed in, so they work inside an `<SVG>` and a
`<Scene>` as they do in a panel.

## What a blok may be made of

The components, their props, and the operations a blok may call (`@utils...`) are
the ones the user interface has. They are written down in a **catalog**, and a blok
is checked against it where it is declared: a component the interface does not
have, a prop it does not take, children where none are drawn, or a callback that is
not bound to a call is refused by `app.blok(...)`, with the place in the tree.

```text
ValueError: <Slidr> (Card/CardContent[0]/Slidr[0]): component 'Slidr' is not
registered in catalog (base@1 + orkestrator)
```

So a typo fails when the app is imported, in its tests and in `arkitekt inspect`,
and is not found out in front of a user.

### The standard catalog

A blok that names no catalog is checked against the standard one, `orkestrator`:
what the Orkestrator app renders. It ships inside `arkitekt-spec`, as a copy of the
`blok-catalog.json` that app publishes with every release, so it is the app that
says what exists and nothing here that could say otherwise.

To see what it holds:

```python
from arkitekt_spec.declare.catalogs import load_standard_catalog, standard_catalog_release

catalog = load_standard_catalog()
standard_catalog_release()                       # 'v2.19.0': the release it is a copy of
[c.name for c in catalog.components]             # Accordion, Alert, Badge, Button, Card, ...
[(p.key, p.kind) for p in next(c for c in catalog.components if c.name == "Slider").props]
```

Three things to know when writing against it:

- **Text is a prop.** `<span text="Hello" />`, not `<span>Hello</span>`; and not
  every component has one (`div` does not: put a `span` in it).
- **An operation of the interface is called by keyword**:
  `@utils.math.round(value=self.Stage.x_um, precision=2)`. Only the base
  operations (`eq`, `gt`, `if`, `coalesce`, ...) take their arguments by position.
- **`className` is not checked.** It is a string of Tailwind classes, and whether a
  class does anything is the interface's to know.

### Another catalog

A blok for another renderer says so, and is then not held to the standard catalog:

```python
app.ui_catalog("electron", components=[ComponentSpec(name="Gauge", props=(...))])
app.blok("dial", "<Gauge />", catalog="electron")
```

A catalog the app declares is what its bloks are checked against. One it only names
(`catalog="somewhere-else"`) is known to the server alone: nothing can be checked
here, and the server says what it finds when the app registers.

## Keeping the copy current

The standard catalog changes only by being copied again, in `arkitekt-spec`:

```bash
python scripts/sync_standard_catalog.py            # the latest Orkestrator release
python scripts/sync_standard_catalog.py v2.19.0    # that one
```

Run the tests afterwards. A blok that used something the new catalog dropped fails
there, which is the point: the drift shows up in the commit that brings it in.

Where the published catalog says something the app does not do, the copy is left as
it is and the difference is set right by name, in `STANDARD_CATALOG_CORRECTIONS`. A
test fails for a correction the catalog no longer needs.
