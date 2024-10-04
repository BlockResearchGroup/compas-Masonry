# Armadillo Vault

![Armadillo Vault, Venice, Italy, 2016 (Copyright photo: Iwan Baan)](https://block.arch.ethz.ch/brg/images/cache/beyond%20bending%204887\_1464606068\_1920x1080.jpg?1464606068)

Comprised of 399 individually cut limestone pieces, unreinforced and assembled without mortar, the Armadillo Vault spans 16 m with a minimum thickness of only 5 cm. Its funicular geometry allows it to stand in pure compression, while tension ties equilibrate the form. Starting from the same structural and constructional principles as historic stone cathedrals, this sophisticated form emerged from novel computational graphic statics-based design and optimisation methods developed by the project team.

## Block Model

![](../.gitbook/assets/armadillo\_breps\_ghosted.png)

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("armadillo.json")

artist = Artist(assembly)
artist.draw_blocks()

```

## Connectivity Diagram

![Connectivity diagram of the block model of the Armadillo Vault](../.gitbook/assets/armadillo-connectivity\_viewer.png)

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("armadillo.json")

artist = Artist(assembly)
artist.draw_blocks(show_faces=False)
artist.draw_nodes()
artist.draw_edges()

```

## Interfaces

![Contact interfaces between the blocks of the Armadillo Vault.](../.gitbook/assets/armadillo-interfaces\_viewer.png)

```python
import compas
from compas.artists import Artist

assembly = compas.json_load("armadillo.json")

artist = Artist(assembly)
artist.draw_blocks(show_faces=False)
artist.draw_interfaces()

```

## Equilibrium

{% hint style="info" %}
Coming soon...
{% endhint %}
