---
sidebar_label: base
title: ui.qtwidgets.base
---

## UIPortMixin Objects

```python
class UIPortMixin()
```

#### get\_current\_value

```python
@abstractmethod
def get_current_value()
```

Gets the current value of the widget or returns None if
no user input was set, or default

**Raises**:

- `NoValueSetError` - An error that this widgets has no current value set

