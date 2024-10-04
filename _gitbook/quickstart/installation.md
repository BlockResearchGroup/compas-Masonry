# Installation

{% hint style="info" %}
Currently, only a "developer installation" is available. A simpler procedure will be made available soon...
{% endhint %}

## Dev Install

The procedure for a "developer installation" consists of the following steps.

### 1. Create Environment

```bash
conda create -n masonry python=3.9 --yes
```

### 2. Install COMPAS packages

```bash
conda activate masonry
conda install compas compas_view2 -c conda-forge --yes
pip install compas_cloud compas_ui compas_assembly compas_masonry
```

### 3. Install User Interface

{% hint style="info" %}
Coming soon...
{% endhint %}

### 4. Install Equilibrium Solvers

{% hint style="info" %}
Coming soon...
{% endhint %}
