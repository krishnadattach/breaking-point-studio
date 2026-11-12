# Impossible Builds — visual style ("X-Ray Grid")

Every visual decision we have approved, and why. The numbers live in
`grid_kit.py` (the single source of truth); this file explains them.
`reference.png` is the approved look (last frame of the panels test, final
quality, 1080×1920). `reference_cutaway.png` is the approved cutaway look.

**Rule:** change the look only in `grid_kit.py`, then update this file and
re-render the references. Episode scripts never set colours, lights, camera
numbers or render settings themselves.

---

## 1. Rendering

| Decision | Value | Why |
|---|---|---|
| Engine | Eevee on the RTX 3070 | Fast, and gives the clean cross-section look. Cycles only when asked. |
| View transform | Standard, look None, exposure 0 | Palette hex colours appear exactly (AgX/Filmic make them paler). |
| Preview | half size, 32 samples | Fast checks. Always approved before a final render. |
| Final | full size, 128 samples | Clean edges and grid lines. |
| Shorts / long-form | 1080×1920 / 1920×1080 | Channel format. |
| Frame rate | 30 fps | Channel format. |
| Motion blur | on | Fast fly-ins streak slightly instead of strobing. |
| Video | MP4, H.264, high quality | Plays everywhere; good enough for previews. |
| Colours in Blender | hex converted to linear | So `#00C2FF` in the kit is `#00C2FF` on screen. |

## 2. Palette

| Name | Hex | Used for |
|---|---|---|
| Electric cyan | `#00C2FF` | The "solution": accent parts, panels, orbit line, flashes, ghost edges. |
| Warning orange | `#FF6B2C` | The "problem"/core: hot parts, the star's mid-tone, its halo and light. |
| Near black | `#0A0B0D` | Background / sky. |
| Floor grey | `#111316` | Floor. |
| Grid grey | `#2C3136` | Floor grid lines. |
| Shell grey | `#3A3F45` | Outer skin of a build. |
| Neutral grey | `#6B7078` | Supporting parts. |

Only two colours plus greys, so the eye goes straight to cyan vs orange.
We never copy another channel's exact look or colours.

## 3. Background, floor and grid

- **Near-black sky** (`#0A0B0D`): makes cyan and orange glow; leaves the top of
  a Short clean for 2D titles added later in Remotion.
- **Floor** `#111316`, 600 m wide so its edge is never in shot (an 80 m floor
  showed its edge once the camera pulled back).
- **Engineering grid**: thin `#2C3136` lines every 0.5 m. Gives scale and the
  "technical drawing" feel; subtle enough not to compete with the build.

## 4. Lighting

- Three soft **white** area lights: key (upper left, 600 W), weak fill (right,
  100 W), rim (behind, 400 W). White keeps the greys neutral — a cyan rim light
  we tried tinted the whole floor blue.
- The lights **ride on the camera rig**, so the look is identical from every
  orbit angle.
- Glowing parts add their own light (see §6).

## 5. Materials by role

| Role | Colour | Roughness | Why |
|---|---|---|---|
| shell | `#3A3F45` | 0.4 | Outer skin stays dark so the inside reads. |
| accent | `#00C2FF` | 0.3 | The part that solves the problem. |
| neutral | `#6B7078` | 0.4 | Supporting structure. |
| hot | `#FF6B2C` | 0.3 | The problem, the core, the warning. |
| ghost | cyan glass, 3 % opaque, glowing edge | — | Shows a removed piece without hiding what's inside. |

Solid parts are semi-matte and never glow (only glowing parts and flashes do).

**Cutaway** (`kit.cutaway`): a wedge is cut out of the build; each inner layer
sticks out by 6 mm so cut faces never flicker; the removed piece stays as the
cyan ghost. See `reference_cutaway.png`.

## 6. Glowing parts — the star (`kit.glow_sphere`)

| Decision | Value | Why |
|---|---|---|
| Surface colour | yellow-orange `#FFC94D` centre → palette orange → deep `#D9480F` rim | Reads as a star, not Mars. Orange on its own looked dull. |
| Brightness | 1.0 at the rim → 1.5 in the middle | Clearly the brightest thing on screen. |
| Brightness limit | brightness comes from the yellow colour, not a huge strength | Red is already full; pushing strength clips everything to flat red/yellow, which wiped out the texture and the crisp edge ("fog ball"). |
| Texture | noise scale 4, ±30 % mottling, stretched to full range | Boiling-gas look; big cells survive half-size previews and video compression (fine texture vanished). |
| Edge | crisp | The halo never covers the sphere (below). |
| Halo size | 1.5 × radius, 30 % at the edge, soft falloff | Thin and soft. A 2.2× / 60 % halo turned the star into an orange fog ball. |
| Halo build | camera-facing ring card **behind** the sphere, with a hole the sphere's size | Can't cover the surface or edge. |
| Halo blend | paints its colour over the background (not added on) | Looks the same on all sides; an added glow vanished over the brighter floor. |
| Height above floor | about 5 radii (floor 3.6 m below a 0.7 m star) | A brightly lit floor right behind the halo washed out its lower half. |
| Nearby light | 250 W orange point light inside | Lights nearby parts in the star's colour. |
| Floor glow | 75° orange spot aimed at the floor patch the camera sees just under the star; rides on the camera rig | Warm pool appears directly under the star on screen and stays there during the orbit. Straight down put it at the bottom of the frame. |
| Floor glow brightness | as bright as a 4500 W light straight overhead | Clearly warm, but the grid still reads through it. |

## 7. Solar panels (`kit.solar_panel`)

- Cyan `#00C2FF`, 0.8 × 0.55 m, 3 cm thick; fine dark cell grid (6 × 4) and a
  thin glowing cyan edge — reads as "solar panel" even at Shorts size.
- **Sunlit panel** (we see the face that looks at the star): deeper cyan
  `#0077A8`, less shine, plus a gentle cyan glow. It's the brightest panel but
  a rich cyan — the plain material washed out to pale blue-white in sunlight.

## 8. Parts on an orbit (`kit.orbit_mount`, `kit.fly_in_on_orbit`)

- **Orbit line**: thin (8 mm) faint cyan circle, radius 1.5 m — shows the path
  without competing with the parts.
- **Mount tilt**: far side tipped up 20°, turned to face the camera halfway
  through its orbit — the part behind the star shows above it, not hidden.
- **Even spacing**: for 3 parts, -60°, 60°, 180° as seen from the camera.
- **Facing**: each part faces the centre but turns up to 30° toward the camera,
  so none is ever seen edge-on as a thin line.

## 9. Camera and framing

| Decision | Value | Why |
|---|---|---|
| Lens | 50 mm | Natural perspective, little distortion. |
| Rig | turntable (`CamRig`) | An orbit is one rotation; lights ride along. |
| Hero shot `orbit` | 12.5 m back, 4.75 m up (~21° down), -50° → -20° | The whole build stays inside the safe zone. |
| Orbit | 30° over 5 s, linear | Slow, steady, shows depth without distracting. |
| Shorts framing | lens shift x +0.03, y −0.03 | Nudges the subject left and up, away from YouTube's buttons and captions. |
| Safe zone (Shorts) | 6–82 % across, 24–94 % up | Our estimate of where YouTube's UI sits; checked with `kit.safe_zone_report`. |
| Other shots | `swarm_wide` (14.5 m, 5.5 m up), `cutaway_closeup` (6.5 m, 3 m up, floor 1 m below) | Bigger builds / close cutaway stills. |

## 10. Motion

- **Motion starts on frame 1.** The first part's flight starts before frame 1
  (70-frame pre-roll), so it's already entering the shot — no empty opening.
- **Every arrival overshoots, settles and flashes once** (`kit.arrive`):
  12 cm past the spot with an 8° twist, settle back over 6 frames, cyan flash
  peaking at landing and fading over 10 frames. Gives a satisfying "snap".
- **Smooth easing** on flights; **linear** on the camera orbit.
- **Waiting parts are hidden** until their flight starts, and every flight
  starts off-screen (2.8× further out, 5 m up, tumbling) — nothing hangs in
  view or pops in.
- **Timing for one-at-a-time arrivals**: landings at frames 30, 68, 106
  (38 frames apart), 28-frame flights, then a hold while the camera orbits.

## 11. Checks before reporting any render

1. Extract a frame (last frame of a video with ffmpeg) and look at it.
2. Check it matches what was asked (close-ups and measurements when in doubt).
3. Safe zone: `kit.safe_zone_report` must say "all clear".
4. After any kit change: render a test shot at final quality and compare it with
   `reference.png` using `compare.py`
   (passes when the average difference ≤ 0.005 and ≤ 0.2 % of pixels visibly differ).

## Tried and rejected

- **Studio Night** (cyan rim light) and **Gallery White** looks — owner picked X-Ray Grid.
- Big thick halo — star became an orange fog ball.
- Added-on (additive) glow — vanished over the bright floor.
- Orange-only star surface — looked like Mars, not a star.
- Floor glow straight down — landed at the bottom of the frame.
- Panels exactly facing the star — side panels went edge-on.
- Panels touching in rings — read as solid bands, not a swarm.
