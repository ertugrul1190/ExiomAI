# EXIOM AI — The Opening

Task 17. The client loved the dive but not its logic: the
brain looked closed and complete, so flying into it and
landing in the chat didn't make sense. A plane window opening
onto clouds works because there is somewhere to go through.
They asked for an opening in the brain to zoom into, and for
the chat to look like the inside of whatever we flew into,
alive with constant motion, in a unique, complementary palette.

The answer is one continuous camera path: **outside the brain,
through an opening, down a tunnel, then inside it.** The chat
is the inside of that same tunnel.

Tests: 528, all passing (with `EXIOM_USAGE_TOKEN` blank; see
Task 8, 8.6).


## 17.1 The opening

The near hemisphere now has a mouth that looks like it is
waiting for you:

* **A shaft cut through the brain**, and the tissue around it
  pushed outwards and lifted towards the viewer, so the nodes
  crowd into a raised **lip**. The lip burns **solar**.
* **A tunnel behind it:** 15 rings of 24 nodes (11 × 18 on
  phones), meshed around each ring and spoke by spoke inwards.
  It narrows as it goes and twists into a helix, running from
  flamingo into aqua. The **core** is now at its far end, in
  the fissure at the centre of the mind, not on the surface.
* **It moves like it's swallowing:** a swell runs down the
  rings, and the tunnel twists to and fro, the deeper rings
  further. Two in five pulses start on the lip, and inside the
  tunnel every pulse heads for the core, so a steady stream of
  light pours into the opening. A soft flamingo light wells up
  from inside.
* **Line of sight:** the tunnel's axis is tilted (`TILT_X`,
  `TILT_Y`) so that from the intro you look straight down it
  to the core. Measured: the core sits within 5px of the
  mouth's centre. The brain's sway went from ±0.42 to ±0.3
  radians so the mouth keeps facing the viewer.
* The lip is also sewn into the brain: each lip node links to
  its two nearest brain nodes.
* **Start button:** its disc is now a small mouth, with a
  solar lip, a flamingo inner glow and the aqua core.


## 17.2 The dive, retold

1. The camera flies to the mouth. It reaches the lip at four
   fifths of its path, then turns and follows the tunnel to
   just in front of the core. The path eases out, so the
   flight slows as it lands.
2. The tunnel's rings fade only in the last 0.1 before the
   camera (brain nodes: 0.45), so they stream past the camera
   instead of vanishing early.
3. Until the bloom, the core's glow is capped at 10% of the
   screen, so the rings converging on it stay visible. The
   bloom starts at 80% of the flight (it was continuous
   before).
4. The chat opens out of the core as before (`--reveal`, now
   at 0.8 on the timeline, with arrivals at 0.88). The flash's
   centre is now pure white, so it matches the canvas's
   saturated bloom and no grey dot shows at the first pixel of
   the reveal.

The zoom tween's ease changed from `power1.in` to `sine.inOut`.
Scroll, the button, the keys, Skip, Escape and the logo's
reverse trip all work unchanged.


## 17.3 The chamber: the chat inside the brain

A second canvas, `#chamber`, sits behind the chat (`z-index:
-1` inside `.app`). It is the tunnel you flew down, slowed to
a drift:

* **Walls:** rings of neurons (30 × 22 on desktop, 22 × 16 on
  phones) on a tube that takes the viewport's shape, so its
  walls run along every edge. The walls fold like cortex. The
  rings drift slowly towards the viewer and wrap round to the
  far end, and the whole tube turns very slowly. Links are
  sparse (70% around the ring, 85% inwards), so the walls read
  as tissue, not a grid.
* **Brainbow palette:** each neuron gets its own hue: violet
  most, then flamingo, aqua and, rarely, solar. The idea comes
  from Brainbow microscopy, where individual neurons are
  labelled in distinct fluorescent colours, the best-known
  images where neuroscience becomes art. The brand's four
  hues already map onto those stains. So the environment gets
  its own distinctive, complementary colour without adding a
  token or undoing the Task 16 palette.
* **The core** glows at the end of the tunnel with a
  heartbeat. Behind the canvas, `.app::before` is now a static
  light at the vanishing point (aqua in flamingo in violet)
  that breathes slowly (transform only), and `.app` has a
  vignette that deepens towards the edges. The old aurora is
  gone; the chamber replaces it.
* **It answers the conversation:** asking a question fires a
  volley of signals down the walls, and while the answer is on
  its way the core swells and brightens, the drift speeds up
  and the signals run faster. It all eases back when the
  answer arrives (`chamber.think(on)`, called from
  `askQuestion` and its `finally`).
* **Readability:** anything near the middle drops to 30%
  brightness, and far rings fade out, so text over the chat
  column stays calm. Phones run at 70% strength.
* **Pointer parallax:** with a mouse, the vanishing point
  drifts up to 3% against the pointer.


## 17.4 Cost and bulletproofing

* The chamber draws about 660 sprites and 3 strokes per frame
  (350 on phones), capped at 45 fps (30 on phones), at a
  pixel ratio of at most 1.5. It runs on `gsap.ticker`, so it
  pauses in a background tab. It skips drawing entirely while
  the intro covers the chat, until the reveal begins.
* Measured in headless Chrome over CDP: a steady 16.6ms a
  frame through the whole dive, tunnel included. There is one
  150ms frame at the instant the stage hides and the chat
  takes over layout.
* **Reduced motion:** there is still no stage, and the chamber
  draws one still frame (redrawn on resize). A change to the
  motion setting at runtime starts or stops the loop.
* **No GSAP:** one still frame. **No 2D canvas:** the canvas
  is hidden. **An error inside a frame:** the loop stops, the
  canvas hides and the CSS light stays. `forced-colors` hides
  the canvas.
* Shared helpers moved to module scope: the colour constants,
  `clamp01`, `sprite()` and `strokeBands()`, which draws links
  in brightness bands and is used by both canvases.
* No new requests, files, fonts or origins, and the CSP is
  unchanged: the canvases are drawn from script, and there is
  no inline `style` attribute.


## 17.5 Verified

Headless Chrome through CDP, at 1440×900 and 390×844 (touch):

* the intro, with the opening centred and a close-up of it
* the dive, frame by frame at set progress points (0.3 to
  0.9): approaching the mouth, inside the tunnel with the
  rings spiralling to the core, the bloom, and the reveal
* the chat's chamber, and the thinking state (with a stalled
  `fetch`)
* reduced motion: no stage, logo disabled, chamber shown still
* the logo round trip: skip, then back home through the
  tunnel, then dive again

There were no console errors or exceptions. 528 tests pass.

Note for future checks: GSAP timelines are thenables. A CDP
`Runtime.evaluate` with `awaitPromise: true` that returns one
(for example `tl.progress(0.5)` or `timeScale()`) waits for the
timeline to complete, which can be never. End such
expressions with `; 0`.


## 17.6 After the Task 16 revision

The palette moved to black, blue and orange (Task 16, 16.6).
The opening and chamber take it through the renamed
constants: the brain is blue with orange nodes, the lip
burns amber, the tunnel runs orange into ice, and the
chamber's Brainbow hues are blue, orange, ice and, rarely,
amber. The dive's flash now clears through ice and orange.
The Skip intro button is gone; Escape still skips, and the
logo's round trip is unchanged.
