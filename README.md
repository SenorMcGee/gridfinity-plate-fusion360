# Gridfinity Helper — Fusion 360 Add-In

A Fusion 360 Python Add-In that generates custom **Gridfinity baseplates** for **3D Printing**, **Laser Cutting**, and **CNC Machining**, with flexible dead-space handling and automatic bed-size splitting.

## Features

- **3 Manufacturing Modes**:
  - **3D Printed**: Standard stepped Gridfinity socket profile (`42 mm` default pitch), rounded outer corners, optional filament-saving `+` cutout with 4 rounded corner magnet tabs (`6.5 × 2.4 mm` magnet pockets + `3 mm` through-holes), and configurable floor thickness.
  - **Laser Cut**: Flat 2D baseplate with Gridfinity foot cutouts (`36.3 × 36.3 mm` nominal with `5.7 mm` ribs), configurable material thickness, kerf compensation, and corner radius.
  - **CNC**: Full-depth 3D Gridfinity socket cavities carved into stock of configurable thickness with tool-diameter corner radius constraints.
- **Dead-Space & Alignment Options**:
  - **Center & pad leftover** or **Cut partial cells** at plate boundaries.
  - Independent **X and Y Alignment**: `Center`, `Start (left/bottom)`, or `End (right/top)`.
  - Configurable **Minimum partial cell** threshold (slivers smaller than this automatically convert to padding).
- **Machine Bed / Work Area Splitting**:
  - Automatically splits oversized plates (e.g. `400 × 400 mm` on a `256 × 256 mm` printer bed) along cell boundaries into balanced tiles, with an optional visual gap in Fusion.
- **Fast Parametric Generation**:
  - Cuts a single seed cell and patterns it using Fusion's native `RectangularPatternFeature`, wrapping all steps into a single timeline group.

## Installation in Fusion 360

1. Clone or download this repository.
2. In Fusion 360, press **Shift+S** (or go to **Utilities** > **Add-Ins** > **Scripts and Add-Ins**).
3. Switch to the **Add-Ins** tab, click the green **+** next to *My Add-Ins*, and select the [`GridfinityHelper`](GridfinityHelper) folder.
4. Select **GridfinityHelper** and click **Run** (optionally check *Run on Startup*).
5. In the **Solid** > **Create** panel, click **Gridfinity Plate**.

## Running Tests

```bash
python -m unittest discover -s GridfinityHelper/tests
```
