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
