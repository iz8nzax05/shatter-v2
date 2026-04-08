# Shatter V2

Interactive physics sandbox where orbs fall, bounce, collide, and crack the floor on impact. The floor deforms permanently and the crack patterns are procedurally generated.

---

## How it works

**Floor deformation** — each impact carves a bowl-shaped dent using a cosine falloff:
```python
falloff = (cos(ratio * π) + 1) / 2
offset = depth * falloff
```
Dents stack — multiple hits at the same spot compound. The floor line is redrawn every frame by sampling all deformations across every 2px column.

**Impact thresholds** — five tiers based on impact force (`speed × size / 20`):

| Force | Result |
|---|---|
| < 8 | Nothing |
| 8–12 | Tiny dent only |
| 12–18 | Small dent + light cracks |
| 18–30 | Normal dent + cracks |
| 30–50 | Deep dent + heavy cracks |
| > 50 | Crater + max cracks |

**Crack generation** — cracks are procedurally grown as wobbly segmented lines. Each segment deflects the angle by a random amount (`±0.3 rad`). At depth 0, each crack has a 40% chance to branch at the midpoint, spawning 1–2 child cracks at ±1.2 rad. Max branch depth is 2. The cracks are drawn once onto a persistent `pygame.Surface` and stay there.

**Slope physics** — the orb samples floor height 5px left and right to estimate slope angle, then gets a lateral acceleration pushing it downhill:
```python
slope_angle = (floor_right - floor_left) / (2 * sample_dist)
velocity.x += slope_angle * gravity * 0.15
```

**Orb collisions** — elastic impulse resolution with restitution 0.6. A sleep threshold (`velocity_along_normal < 0.02`) prevents vibration when two settled orbs are touching.

**Impact cooldown** — a 60-frame cooldown (1 second) prevents the same orb from triggering multiple impacts on a single bounce. The orb must also be airborne for at least 5 frames before landing to count.

---

## Controls

| Input | Action |
|---|---|
| Click | Spawn orb |
| Click + Drag | Pick up and throw orb (glows yellow while held) |
| Release | Apply throw momentum |
| `C` | Clear canvas |
| `Tab` | Toggle UI panel |
| `D` | Toggle debug markers (dent centers + radius rings) |

---

## UI

The panel at the top (toggle with Tab) has:
- **Gravity** slider — 0.1 to 5.0
- **Orb Size** slider — 10 to 100px
- **Clear Canvas** button
- **Toggle FPS** button

---

## Running it

```bash
pip install pygame
python shatter_v2.py
```

**719 lines**, single file.
