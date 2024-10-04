# Coupled Rigid Block Analysis

![](https://lh3.googleusercontent.com/zaPjTHQjzaR0BLMCb48Umn0ZjizBNgUw31csuJrYF37-PuV9WpsRUh-Xl6P5noQ7ZvhKof\_6jfeZK1JO8iPG8RSp8NgmGHpHmN3mGQbUM-vWT\_owq8kZI2QykuUdT\_PrSuTclKx\_)

The rigid-block equilibrium (RBE) method uses a penalty formulation to measure structural infeasibility or to guide the design of stable discrete-element assemblies from unstable geometry. However, RBE is a purely force-based formulation, and it incorrectly describes stability when complex interface geometries are involved. Coupled rigid-block analysis (CRA) method is a more robust approach that builds upon RBE’s strengths and overcomes the aforementioned issues. The CRA method combines equilibrium and kinematics in a penalty formulation in a nonlinear programming problem. CRA enables accurate modelling of complex three-dimensional discrete-element assemblies formed by rigid blocks. CRA’s accuracy is benchmarked against widely used software in engineering practice and demonstrated through physical models.

## compas\_cra

compas\_cra provides a base implementation of CRA. Additionally, _compas\_cra_ can also be applied to masonry with curved interfaces.

{% embed url="https://blockresearchgroup.github.io/compas_cra" %}
compas\_cra docummentation
{% endembed %}

{% embed url="https://github.com/BlockResearchGroup/compas_cra" %}
compas\_cra open-source repository
{% endembed %}
