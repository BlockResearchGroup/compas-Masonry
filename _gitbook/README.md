---
description: Practical Assessment Tools for Historic Masonry Structures
---

# COMPAS Masonry

{% hint style="warning" %}
Note that this website is under construction and will be updated frequently!
{% endhint %}

[![DOI](https://zenodo.org/badge/458133035.svg)](https://zenodo.org/badge/latestdoi/458133035)

**COMPAS Masonry** is a computational toolbox for the stability assessment of historic masonry structures under various loading conditions.

The assessment and preservation of (historic) masonry structures is a complex engineering problem that requires specific analysis tools and collaboration between various experts to determine if a structure is still safe, especially after significant settlements or changing boundary conditions.

COMPAS Masonry integrates different numerical analysis methods in a unified framework, offering a wide range of assessment options to both academic researchers and professional engineers.

## Open source collaboration

COMPAS Masonry is built on top of [COMPAS](https://compas.dev/), an open-source framework for research and collaboration in Architecture, Engineering, Fabrication, and Construction.

Like COMPAS, COMPAS Masonry is entirely open source and free and based on peer-reviewed, state-of-the-art research.

## AEC Software

COMPAS Masonry is developed independently of CAD applications. As a result, it can be integrated with different CAD software. Currently, implementations are available for Rhino 6+ and Blender.

<figure><img src=".gitbook/assets/image (11).png" alt=""><figcaption><p>Compas TNO in Rhinoceros finding admissible stress states in vaulted masonry structures.</p></figcaption></figure>

Beyond CAD applications, COMPAS masonry user interface is also available through a standalone UI, enabling the structural analysis entirely from Python.

![Equilibrium of two blocks computed with COMPAS RBE visualised in the Python Viewer](.gitbook/assets/compas-ui.gif)

## Data structure

COMPAS Masonry offers a data management structure which makes it easy to work with discrete masonry elements.

From the point of view of geometry, having multiple discrete elements bring a layer of geometric complexity which is dealt with by the data structure developed. Furthermore, COMPAS Masonry enables data exchange between solvers and stores various masonry mechanics properties.

## Working with real data

Geometry acquisition is a big challenge when assessing masonry structures. This acquisition is usually the result of laser scan and photogrammetry processes, which are not directly integrated with the structural analysis. COMPAS Masonry has specific algorithms and routines that ease this conversion process and allows working with surveyed data such as point clouds.

![Point Cloud Survey of the dome in the Santo Agostino Church, Anagni, Italy. Courtesy P. Fuentes and S. Guerra, 2019.](<.gitbook/assets/image (12).png>)

## Parametric Geometries

As an alternative to surveyed data, parametric geometry models are crucial for assessing existing structures or for more theoretical research studies on masonry. For this purpose, inside COMPAS Masonry, the parametric models for generating the most common historical structural typologies have been implemented. Staggered walls, rounded or pointed arches, pavilion and cross vaults, and domes can be quickly generated with a varying span, thickness, springing angles, and block dimensions.&#x20;

![Parametric Geometries created wth COMPAS masosnry correspsonding to commom masonry typologies.](https://lh5.googleusercontent.com/ilnXqOKT6xmuz\_Zc4v8bbHFbRNsKUeDNM6PJj1b3Wr\_PINhDyU\_Nd6tZzY3rVc\_xGPcHX-l-O9KwTrbY7zMf324J\_b61K7maa3yNsyfxlnhmg8r7t1DstoOAv7KLXB4kB4m2qW2d)

## **State-of-the-art equilibrium solvers**

Within the COMPAS Masonry project, a series of state-of-the-art equilibrium solvers has been developed and implemented. Among these solvers are Rigid-Block equilibrium (RBE), Coupled Rigid-Block Analysis (CRA), Piecewise-Rigid Displacement (PRD), and Thrust Network Analysis (TNA).

![Extensions of COMPAS associated with COMPAS Masonry.](<.gitbook/assets/image (5).png>)

These solvers are developed in separated sub-packages and integrated through COMPAS Masonry. For more information about each solver, visit our [solvers page](broken-reference).

## Interface with professional software

COMPAS masonry can provide an interface to professional software such as the Discrete Element Modelling software 3DEC by Itasca. 3DEC files with geometrical data and the analysis setup can be directly generated through COMPAS masonry. Moreover, after the analysis, 3DEC results can be post-processed using customised scripts and visualised together with the deformed geometry in the COMPAS viewer or other CAD software, plotting useful information for the structural assessment.

<figure><img src=".gitbook/assets/image (1).png" alt=""><figcaption><p>Collapse of pavillion vault after support displacements. (Dell'Endice et al., 2021)</p></figcaption></figure>

More details about the development of such application can be found in the [professional software page](broken-reference).

## Funding

The present work was supported by the SNSF - Swiss National Science Foundation. Project grant n 178953: “Practical Stability Assessment Strategies for Vaulted Unreinforced Masonry Structures”. More details about the research output of this project are available [here](additional-info/snsf-project.md).
