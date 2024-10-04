# Dome

## Block Model

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("crossvault.json")

artist = Artist(assembly)
artist.draw_blocks()

```
