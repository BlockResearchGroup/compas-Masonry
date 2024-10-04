# Cross Vault

## Block Model

![Block model of a cross vault generated with a parametric template.](../.gitbook/assets/try\_crossvault\_blocks-rhino.png)

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("crossvault.json")

artist = Artist(assembly)
artist.draw_blocks()

```
