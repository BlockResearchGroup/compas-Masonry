# Striatus

![Striatus - 3D concrete printed masonry bridge, Venice, Italy, 2021.](https://block.arch.ethz.ch/brg/images/cache/striatus\_brg-zha\_%C2%A9naaro\_10\_16x9\_1626689552\_1920x1080.jpg?1626689552)

Striatus is an arched, unreinforced masonry footbridge composed of 3D-printed concrete blocks assembled without mortar. Exhibited at the Giardini della Marinaressa during the Venice Architecture Biennale until November 2021, the 16x12-metre footbridge is the first of its kind, combining traditional techniques of master builders with advanced computational design, engineering and robotic manufacturing technologies.

## Block Model

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("striatus.json")

artist = Artist(assembly)
artist.draw_blocks()

```

## Connectivity Diagram

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("striatus.json")

# assembly_interfaces_numpy(assembly, tmax=0.02, amin=0.10)

artist = Artist(assembly)
artist.draw_blocks(show_faces=False)
artist.draw_nodes()
artist.draw_edges()

```

## Interfaces

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("striatus.json")

artist = Artist(assembly)
artist.draw_blocks(show_faces=False)
artist.draw_interfaces()

```
