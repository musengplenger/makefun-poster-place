# VELMORA — The Glass Tide Coast

A 1024x1024 travel poster for a fictional place: a twilight coast where the
sea glows glass-green, a natural rock arch frames a low amber moon, a
lighthouse sweeps its beam across the water, and one traveller stands on the
shore looking out at the sea.

## Run

```sh
python3 main.py
```

Writes `/output/entry.png` (deterministic — the same bytes on every run).

## How it is drawn

Pure Pillow, no network, no external assets: layered gradients for the dusk
sky and the teal sea, a glowing moon with a shimmering reflection path, a
rock-arch silhouette with an amber rim light, cliffs, a lighthouse beam, one
person, film grain and a vignette. Fonts are the system DejaVu faces.
