# Rigid Block Equilibrium

![Interface forces of the RBE formulation.](https://lh4.googleusercontent.com/wx\_UoU3CDESLUk2ZnZFrhzb6Bj-4b\_fjQkIB0FJB7ZVk9iulaZrEcwywpyuVhVkzzXv8LM4oztAF1rEKCPyI2KfaeLt6pmD0nicL8yfLrRgUgZSKrZnCszc0AP-UwOZOz6YnVmlE)

Rigid-Block Equilibrium (RBE) is a numerical approach that frames the equilibrium problem of rigid-block assemblies as an optimisation problem to compute possible internal and equilibrated singular stress states. The contact between blocks is considered to have a finite friction capacity, and the unilateral behaviour is modelled through a penalty formulation. In particular, the penalty formulation widens the standard admissible solution space of compressive-only forces by allowing for tensile forces to appear in potentially unstable regions.

## compas\_rbe

The RBE objective function minimises the interface forces, whereas the constraints are linear functions enforcing the static equilibrium of the whole assembly. _compas\_rbe_ provides a base implementation of RBE. In _compas\_rbe_, blocks are considered infinitely rigid and have infinite compressive strength. compas\_rbe provides the necessary contact forces (i.e. compression, tension and friction forces) for the assembly to be in equilibrium under given external loads.

{% embed url="https://blockresearchgroup.github.io/compas_rbe/" %}
compas\_rbe docummentation
{% endembed %}

{% embed url="https://github.com/BlockResearchGroup/compas_rbe" %}
compas\_rbe open-source repository
{% endembed %}
