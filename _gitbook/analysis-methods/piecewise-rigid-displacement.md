# Piecewise Rigid Displacement

![](<../.gitbook/assets/image (8).png>)

The piecewise rigid displacement (PRD) method represents the extension of the Heyman model to continuum mechanics through the use of a normal, rigid, no-tension (NRNT) material. It couples the kinematic problem (KP) with the equilibrium problem (EP) using two dual, energy-based criteria.

## Background

In particular, the KP is solved by minimising the total potential energy that allows to find displacement and crack patterns compatible with external loads and non-homogeneous boundary conditions. Conversely, the EP is solved by minimising the complementary energy which allows defining internal stress states in equilibrium with external loads and compatible with displacement-like boundary conditions. Because of the no-sliding assumption, it can be proved that the two energy criteria are dual, meaning that the solution of one of these two problems can be directly defined from the solution of the dual problem.

The PRD method frames the minimum of the potential energy in the space of the piecewise rigid displacement fields, while the minimum of the complementary energy in the space of singular stress fields. Additionally, it discretises both minima as two dual linear programming problems.

Its use allows addressing different mechanical problems: equilibrium and stability of the reference configuration, effects of settlements, and mechanisms due to overloading (e.g. horizontal forces). Since the NRNT material represents the extension to continuum media of Heyman’s material model, the PRD method offers an extremely fast, limit analysis-based, displacement approach that allows simultaneously finding mechanisms and compatible internal forces for any boundary condition, loads and geometry.
