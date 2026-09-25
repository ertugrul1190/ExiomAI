# EXIOM AI — Vibrant Redesign

Task 16. The client found the Task 8 indigo too dull and
asked for bold, joyful, modern colour, more interactive
components, glass and transparency, and for the start
button to be the most attractive thing on the page. The
layout, the brain, the dive and every chat behaviour from
Tasks 8 and 9 are unchanged.

Tests: 528, all passing (with `EXIOM_USAGE_TOKEN` unset; see
Task 8, 8.6).


## 16.1 Palette: "ultraviolet sunset"

The field moves from blue to a plum night. Each colour keeps
one job:

| Token | Hex | Used for |
| --- | --- | --- |
| `--deep` | `#13051F` | Background (plum, not a tinted black) |
| `--raised` | `#1F0A33` | Composer |
| `--ink` | `#FFF3FA` | Text |
| `--muted` | `#BCA8D9` | Secondary text (≈8.5:1 on `--deep`) |
| `--violet` | `#A58BFF` | The mind: links, brain nodes and links, the logo ring |
| `--flamingo` | `#FF4FAE` | Energy: every action, a third of the brain's nodes |
| `--solar` | `#FFC53D` | Energy: end of the action gradient |
| `--aqua` | `#3CF0E2` | Only what is live: pulses, the core, live dots, focus rings |
| `--on-hot` | `#1C0626` | Text and icons on the gradient (≈6:1) |

`--hot` is the one gradient (flamingo → coral → solar), worn
by the start button, the send button, the streaming switch,
the caret and the message mark. `--glass` and `--glass-edge`
are the translucent fill and edge for glass surfaces. The
old `--iris` and `--mint` tokens were renamed to `--violet`
and `--aqua`, and the brain's `IRIS` and `MINT` constants
changed with them. `usage.css` only uses the shared tokens,
so the usage page picks up the palette without edits.

**Type.** Still Mona Sans, self-hosted, but the display lines
are now heavy (800) and expanded (125%) instead of light
(300). Both the intro title and "What do you want to know?"
use a gradient (ink → pink → solar). The gradient is set
under `@supports (background-clip: text)`, and
`forced-colors` resets it to plain text.


## 16.2 The start button

It says **"Start chatting"** (it was "Start asking"), because
that is what the client calls it.

* Filled with `--hot`, heavy expanded label, and a dark disc
  on the right holding an aqua core. That is the node the dive
  flies into, and it beats like the other live dots.
* A blurred conic colour wheel (flamingo, solar, aqua,
  violet) turns behind it. It animates a registered
  `@property --spin`. Where `@property` is missing, the wheel
  is still there but doesn't turn. This is the only thing on
  the page that moves on its own apart from the brain.
* Hover: it lifts and scales with a spring, the wheel widens
  and brightens, the core turns 90°, and a light follows the
  pointer. Press: it scales down. Focus: aqua ring, offset
  6px.
* On mobile it is full width, with the label left and the
  core right.


## 16.3 Components

* **Suggestions** are now glass tiles (`backdrop-filter`),
  each in its topic's colour through `data-tone`: explain in
  violet, service nodes in solar, privacy in flamingo, and
  the live snapshot in aqua. Aqua is the "live" colour, and
  that one reads the chain, so its dot beats. Hover lifts the
  tile with a spring, lights its border, casts a coloured
  shadow, grows the dot, and a light follows the pointer.
  Press scales it down.
* **Pointer light:** one passive `pointermove` listener in the
  app script sets `--mx` and `--my` on any `[data-glow]`
  element through the CSSOM. The CSP allows this: there is no
  `style` attribute and no inline handler.
* **Chat background:** a slow aurora (flamingo, violet, solar)
  on `.app::before`. It animates transform only, so it costs
  only the compositor.
* **Header** is frosted glass. **Chips** and **"Skip intro"**
  are glass pills.
* **Composer:** a gradient border (violet → flamingo → solar)
  that goes to full strength with a flamingo glow on focus.
  **Send** wears `--hot` and tilts up on hover.
* **Your messages** use a violet → magenta gradient bubble
  with white text (≥5:1 at both ends).
* **Thinking** fires flamingo. **Streaming switch** turns
  `--hot` when on.
* **Brain:** violet nodes and links, every third node
  flamingo, aqua pulses and core. The dive's flash clears
  through aqua and flamingo.


## 16.4 Bulletproofing

* `prefers-reduced-motion`: the existing rule still stops the
  wheel, the aurora and every transition.
* Touch screens (`hover: none`) keep `:hover` after a tap, so
  tiles and buttons don't stay lifted or lit.
* No new requests, fonts or origins, and the CSP is
  unchanged. `theme-color` is now `#13051F`.


## 16.5 Verified

Headless Chrome through CDP, 1440×900 and 390×844: the intro
settles, the start button's hover state, the dive into the
chat, and a hovered suggestion tile. There were no console
errors or exceptions. 528 tests pass.


## 16.6 Revision: black, blue and orange

The client's second round: the "Miami" colours didn't fit
the vibe; the start button was small and tucked bottom left;
the brain was the only interesting thing on the page and the
background looked plain; Skip intro and the streaming switch
should go (streaming is always on); and the landing should
welcome people by name, credit Xrypto, and say kindly what
ExiomAI is for.

**Palette: "signal fire".** Black, lit by blue and orange.
Every token keeps its Task 16 job; only the colour (and the
name) changed. The names now say the colour, in CSS, the
`data-tone` values and the canvas constants (`VIOLET` →
`BLUE`, `FLAMINGO` → `ORANGE`, `SOLAR` → `AMBER`, `AQUA` →
`ICE`):

| Token | Hex | Used for |
| --- | --- | --- |
| `--deep` | `#020409` | Background (black) |
| `--raised` | `#0B1322` | Composer |
| `--ink` | `#F3F6FC` | Text |
| `--muted` | `#98A8C4` | Secondary text (≈8:1 on `--deep`) |
| `--blue` | `#3D8BFF` | The mind (was `--violet`) |
| `--orange` | `#FF7A1A` | Energy, every action (was `--flamingo`) |
| `--amber` | `#FFB23F` | End of the action gradient, the lip (was `--solar`) |
| `--ice` | `#8FE6FF` | Only what is live (was `--aqua`) |
| `--danger` | `#FF7B72` | Errors |
| `--on-hot` | `#1A0B00` | Text and icons on `--hot` |

`--hot` is now `#FF5B14` → orange → amber. The display
gradient runs ink → pale blue → blue. Your messages are a
blue bubble (`#2563EB` → `#1B3FA8`, white text ≥5:1).
`theme-color` is `#020409` on both pages.

**The landing.**

* **Title:** "Welcome to" (small, 0.34em) over **ExiomAI**
  (huge). It is now an `h2`; the load animation still raises
  both lines.
* **"by Xrypto":** the name links to
  <https://youtube.com/@xrypto_cryptozone> (new tab,
  `noopener noreferrer`). It is dressed as a play button in
  orange, a ring ripples out of it, and a "Click here" tag
  nudges towards it. Hover fills it orange and the tag steps
  aside; press scales it down. Screen readers hear "Xrypto on
  YouTube (opens in a new tab)"; the tag is `aria-hidden`.
* **Lede:** "Crypto shouldn't make anyone feel lost. ExiomAI
  is your one-stop guide to EXIOM: ask about XEQM, service
  nodes or privacy in your own words, and get answers anyone
  can follow, with live numbers from the Official EXIOM
  Explorer. No question is too small."
* **Layout:** on wide screens the copy is centred vertically
  beside the brain, not pinned to the foot. Narrow and
  portrait screens keep it under the brain.
* **Start chatting** is much bigger: 80px tall, a 1.25–1.5rem
  label and a 60px mouth (52px on phones, full width).
* **Background:** behind the brain, a lattice of network
  nodes drifts one cell diagonally and loops, and blocks of
  light run along its wires (three orange across, three ice
  down). CSS only, six `<i>` in `.stage-field`, transform
  only, masked so the copy's side stays quiet. Reduced
  motion never shows the stage; `forced-colors` hides it.

**Removed.** The Skip intro button (Escape and the logo
still skip and return), and the streaming switch with its
`localStorage` setting and the `askOnce` client path: every
answer streams. The server's `/ask` route is untouched.

**Fixes.**

* The start button's colour wheel was painting over its own
  face: inside the button's stacking context a `z-index: -1`
  layer paints above the button's background. The face is
  now `::after`, laid after the wheel, carrying the pointer
  light through a registered `--light`.
* The intro's key handler treated Enter on any non-button as
  "dive". It now skips links too, so Enter on Xrypto opens
  the channel.

**Verified.** Headless Chrome over CDP at 1440×900 and
390×844 (touch): the landing, the start button's hover, the
dive into the chat, and Enter on the focused link (not
intercepted). There were no console errors or exceptions.
528 tests pass.


## 16.7 Links, Buy XEQM and the small print

**Status line.** "AI Online" is gone. Both chips (landing
and chat) take turns, every 6 seconds, at a friendly line:
"Awake and ready to help", "Jargon translator: on", "No
question too basic", "Fully caffeinated", "Zero judgement,
promise", "Reading the chain for fun", "Plain words only",
"Service nodes? Ask away". The first is picked at random.
While an answer is being written they say "Thinking it
through…". The rotation pauses in a background tab and never
runs with reduced motion. Slots are `[data-quip]`; the
lines are `QUIPS` in the app script.

**Buy XEQM.** A second action beside Start chatting, in blue
glass so it never outshouts it. Opens
<https://nonkyc.io/market/XEQM_USDT> in a new tab. Full
width under Start chatting on phones.

**Two rows of links** at the foot of the landing. The colour
says whose they are:

* *Made by Xrypto*: orange circles, the maker's colour from
  "by Xrypto". Discord, YouTube and Telegram, icons only,
  each with an `aria-label` and a tooltip.
* *Official EXIOM*: blue pills, the brain's colour.
  Telegram, Website, Explorer, Dashboard and Exchange, icon
  and name. On phones the names hide (still read by screen
  readers, still tooltips).

Every link opens in a new tab with `noopener noreferrer`.
The icons are one inline SVG sprite of `<symbol>`s, used by
`<use href>`: no requests, no CSP change.

**Disclaimer.** Small print beside the links on wide
screens, under them on narrow ones: an independent,
third-party tool by Xrypto, not an official EXIOM product;
AI answers can be wrong or out of date; not financial,
investment or tax advice; crypto is volatile; links are not
endorsements. The chat's privacy note also gained "Answers
can be wrong and are not financial advice."

**Fit.**

* The title scales with height too (`min(8vw, 13vh)`), so a
  1366×768 laptop fits the whole landing.
* On phones the copy rises into the brain: the brain sits
  higher (`oy` 0.26 in portrait under 600px), and a dusk
  (`.stage-ui::before`) darkens behind the copy. `.stage-ui`
  is now `z-index: 0` so that layer sits above the canvas.
* Phones shorter than 800px drop the lede. The chat's
  welcome says the same.

**Verified.** Headless Chrome over CDP at 1440×900, 1366×768,
390×844, 360×780 and 375×667: everything fits, nothing is
cut off, and the status line rotates. No console errors.
528 tests pass.


## 16.8 Logo and the name ExiomAI

**Logo.** The client's `static/logo.png` (1254px, 1.2 MB) is
kept as the source but never served. Cropped to the badge
and resized with `sips`: `logo-128.png` (the brand mark,
30px, on the landing, in the chat bar and on the usage page),
`favicon-32.png` and `apple-touch-icon.png`, all linked with
`asset_version`. The old SVG ring and core mark and its CSS
are gone; hovering the chat's logo now glows blue and tilts
it.

**Name.** "EXIOM AI" and "XEQM Hub" are now **ExiomAI**
everywhere: page titles, the UI, error messages, the system
prompts, the router prompt, the canned greeting and
identity replies, `knowledge/*.md`, and the old
`frontend/`. The coin and its ticker stay XEQM (Buy XEQM,
`XEQM_USDT`), and so do the project's names (EXIOM, XEQM
Labs). The identity fast path matches "exiom ai" and
"exiomai" alike, with two new test cases. 530 tests pass.
