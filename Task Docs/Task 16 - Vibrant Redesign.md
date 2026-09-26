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


## 16.9 Revision: the client's palette, "deep water"

The client supplied a palette, in priority order: black
`#0B0C10`, slate `#1F2833`, off-white `#C5C6C7`, teal
`#66FCF2` and darker teal `#45A29D`, and asked to keep our
orange. As in 16.6, every token keeps its job; only the
colour (and the name) changed. The two teals take blue's and
ice's jobs: the calmer darker teal covers the most ground
(the mind), and the bright teal is the light (what is live).
Orange and amber stay the energy (but see "Start button and
question bar" below). Renamed in CSS, the `data-tone` values and the
canvas constants: `--blue` → `--teal`, `--ice` → `--aqua`,
`BLUE` → `TEAL`, `ICE` → `AQUA`.

| Token | Hex | Used for |
| --- | --- | --- |
| `--deep` | `#0B0C10` | Background (client black) |
| `--raised` | `#1F2833` | Composer, the start button's disc (client slate) |
| `--ink` | `#C5C6C7` | Text (client off-white; 11.4:1 on `--deep`, 8.7:1 on `--raised`) |
| `--muted` | `#8B949E` | Secondary text, off-white toward slate (6.4:1 / 4.8:1) |
| `--teal` | `#45A29D` | The mind: links, brain nodes and links, washes, lines (6.4:1 as text) |
| `--orange` | `#FF7A1A` | Energy: the send button, the status chip, the message mark, the brain's warm nodes (unchanged) |
| `--amber` | `#FFB23F` | End of the action gradient (unchanged) |
| `--aqua` | `#66FCF2` | Only what is live: pulses, the core, live dots, focus |
| `--danger` | `#FF7B72` | Errors (unchanged) |
| `--on-hot` | `#1A0B00` | Text and icons on `--hot` (unchanged, 6.2:1) |

**Other colour changes.**

* New `--deep-rgb` and `--ink-rgb`. The vignette, the
  landing's dusk and the chat's scrim now use `--deep-rgb`
  instead of hard-coded blue-blacks. `--glass` and
  `--glass-edge` use `--ink-rgb`.
* Display gradient: ink → aqua → teal (it was ink → pale blue
  → blue).
* Your messages are a teal bubble (`--teal` → `#3A8A85`) with
  `--deep` text, at least 4.8:1. White on teal would be 3:1,
  which fails.
* The start button's disc is slate (`--raised`) instead of navy.
* The brain's `WHITE` sparkle is the off-white.
* `theme-color` is `#0B0C10`. `usage.html` never had one
  (16.6 was wrong about that), so it gained it. `usage.css`
  only uses tokens, so it needed no edits.
* The client's logo stays blue: it is their artwork, and we
  don't recolour it.
* The dev-only `frontend/` is untouched (Task 12).

**Verified.** No old palette values are left in `static/`
or `templates/` (grep). Headless Chrome at 1440×900 with
reduced motion: the chat screen reads well, teal and aqua on
black and slate, with orange for the send button and prompt
dots. 528 tests pass. The 2 usage-page tests fail only when
`.env` sets `EXIOM_USAGE_TOKEN`, as before this change (see
Task 8, 8.6).

**Start button and question bar.** The client asked for
the question bar to have no orange in any part, and for the
start button not to be orange. Both now wear a new gradient,
`--cool` (`--teal` → `--aqua`), with `--deep` text and icons
(6.4:1 on teal and above).

* **Start chatting:** a `--cool` face, an aqua glow, and a
  colour wheel of aqua, teal and off-white. The mouth is
  slate into black with a teal lip and a faint aqua glow
  (the lip was amber and orange).
* **Question bar:** the edge is teal → aqua (it was teal →
  orange → amber), and on focus it is `--cool` with an aqua
  halo. The send button is `--cool` (later orange again; see
  "Third round" below). The caret is aqua, and
  selected text in the box is teal (the page-wide selection
  is still orange).
* `--hot` still covers the other actions: the streaming
  caret, the message mark and (until the third round) the
  Xrypto play button.

**Verified.** Neither component's rules, including the
mobile, reduced-motion and `forced-colors` overrides, refer
to `--orange`, `--amber` or `--hot` any more (grep).
Headless Chrome drew both on the real stylesheet: teal
throughout, with dark text that reads well.

**Xrypto's links.** The client asked for Xrypto's social
links (Discord, YouTube, Telegram) to look like the Official
EXIOM links. They were orange icon-only circles
(`.link-icon`, 16.7). Now they are the same `.link-pill` as
the project's links: teal edge and fill, an aqua icon (the
same icons) and an off-white label. Like the project's
links, they show icons only on phones. Their `aria-label`s
("Xrypto on Discord (opens in a new tab)") still say whose
they are and include the visible label. `.link-icon` and
its rules are deleted, so nothing uses it any more. Headless
Chrome at 900px and 390px: the two rows are the same.

**Third round.**

* **Send button:** orange again (`--hot`, `--on-hot` icon,
  orange glow). The rest of the question bar (edge, focus
  halo, caret, selection) stays teal.
* **Status chip:** one line only, **"Awake and ready to
  help"**. The `QUIPS` list, its random start and its
  6-second rotation are gone; `QUIP` is a single constant.
  While an answer is being written, the chip still reads
  "Thinking it through…", then goes back. Both chips (on the
  landing and in the chat) have `.is-status`: an orange edge
  and fill, amber text (≈10:1 on black) and an orange dot.
* **Xrypto play button** (under the main heading): teal, with
  no orange. The edge, fill and ripple are teal, the name is
  aqua, and the play disc is `--cool` with a `--deep`
  triangle. On hover it fills teal with `--deep` text (6.4:1)
  and the disc turns black with an aqua triangle.

**Verified.** The inline scripts pass `node --check`.
Headless Chrome drew the status chip, the Xrypto button and
the question bar on the real stylesheet: orange chip, teal
Xrypto, teal bar with an orange send button.

**Start button core.** The glowing dot inside Start
chatting's mouth (`.cta-core::before`) is orange now, with
an orange halo and glow; it was aqua. The face, the wheel
and the teal lip are unchanged. It still beats.

## 16.10 Feedback and support

The client asked for two words opposite the link rows:
**Feedback** and **Support**. Clicking one opens a small card.

- **Feedback:** "Send feedback on Telegram to
  @Xryptoforgood". The handle links to
  `https://t.me/Xryptoforgood` in a new tab.
- **Support:** "Support ExiomAI by sending some XEQM to:",
  then the address
  (`Wu11Wgeu8ZSFttNS65XWyTAGToF9ypwxUS3qehwDQuhPa3231bq72MFAfZf9UWVaC8HvA5QakHp74Y9sK8aJxsxy1s9MgXGHbc`)
  and an orange **Copy address** button.

**Look.** The words are plain text buttons in `--ink` with a
dotted teal underline. They turn aqua with a solid underline
on hover or while their card is open. Each card opens upwards
and is opaque black with a teal wash, a teal hairline edge,
a 14px radius and a soft aqua glow. It springs in with
`--spring` through `@starting-style` (older browsers simply
show it). The address is aqua monospace in a `--wash` well. It
wraps anywhere, and one click selects all of it. Copy address
uses `--hot` with `--on-hot` text, the same as the send button.

**Layout.** On wide screens `.stage-foot` is a two-column
grid. The `.foot-asks` sit at the right, level with the last
link row, and the small print spans both columns. Each card
is `min(24rem, 100vw - 2 * gutter)` wide, so it never
overflows.

**Behaviour.** The buttons use the disclosure pattern
(`aria-expanded`, `aria-controls`, and a `role="group"` card
right after its button in tab order), and only one card is
open at a time. A card is shown by the `is-open` class, not
`hidden`, so the small print can use the same wiring (see
below). Clicking outside closes it. Escape closes it
and returns focus to the button. It is caught in the capture
phase with `stopImmediatePropagation`, so it no longer also
skips the intro, but only while a card is on screen.
Otherwise the intro's Escape works as before. Copy writes
to the clipboard in a secure context. Otherwise, or if the
write is refused, it selects the address for a manual copy.
The button and a polite live region say "Copied" or
"Selected, now copy it" for 2 seconds. Everything is wired
in the nonced script, with no inline handlers (CSP).

**Verified.** Headless Chrome at 1440×900, 820×1180 and
390×844, with the intro running: both buttons pass a hit
test, every card fits the viewport with no horizontal
scroll, Escape closes a card while the intro stays open, and
an outside click closes it. The inline script passes
`node --check`. The first test run caught Escape skipping the
intro when it was dispatched on `window` itself;
`stopImmediatePropagation` fixed it. Of 530 tests, 528 pass.
The two that fail are the usage-token tests, which fail only
because of a local `.env` token (17.7).

**Tablets and phones.** The client found the foot cluttered
on smaller screens: the link rows, a lone row for the two
words and a centred block of small print, each aligned
differently. It now reflows at each size.

- **Tablets (900px or narrower, or portrait):** `.link-rows`
  becomes `display: contents`, and the foot is one wrapping
  flex line-up. Feedback and Support sit at the right of
  Xrypto's short row, as on desktop, with the Official EXIOM
  row under it. If that row fills up, the words wrap under
  it, still right-aligned. The cards open from the right, as
  on desktop.
- **Phones (600px or narrower):** both groups share one strip
  of icons. Each group is a small grid with its caption
  ("Made by Xrypto", "Official EXIOM") above its icons, and a
  teal hairline separates them. The words and the small
  print are centred under the strip, on the same axis, and
  each card is centred over the words. The grids' column
  counts (3 and 5) match the pills in each row. An added pill
  wraps to a new line rather than breaking the layout.
- **Small phones:** pills are 34px wide at 400px or narrower
  and 28px below 355px, which is still above the 24px minimum
  touch target, so the strip stays on one line. Below 300px
  the groups stack and the hairline is dropped. Phones 620px
  tall or shorter get a smaller heading (`--title-size:
  3rem`), a smaller start-button core (44px) and tighter
  gaps. At 320×568 the name now clears the top bar and the
  small print ends on screen.

On tablets and phones the order on screen differs from the
keyboard order: `order` puts the words before the Official
EXIOM links on tablets, but Tab still reaches both link
groups first and the words last. Each group stays together,
so this is harmless.

**Verified (reflow).** Headless Chrome at 1440×900, 820×1180,
768×1024, 600×900, 390×844, 375×667, 360×740 and 320×568:
the link groups, words, small print and the two main buttons
never overlap, and nothing scrolls sideways. Both words pass a
hit test, every card fits, and Escape and outside clicks
still close the cards without leaving the intro. The phone
strip stays on one line down to 320px.

**Small print on phones.** Even after the reflow, the six
lines of small print were the heaviest thing on a phone
landing. At 600px or narrower it now folds to one centred
line, "Not official EXIOM, not financial advice.", followed
by a **Small print** word (`.foot-gist`, hidden on wider
screens). The two key warnings stay visible without a tap.
Small print is a third `.ask-toggle`. It opens the real
`.disclaimer` (`id="small-print"`, every word intact, never
duplicated) as a card in the same style as the others,
centred over the foot. Clicking outside, Escape or
opening another card closes it. On tablets and desktop the
disclaimer shows in full, as before, and the word never
appears. Escape is only caught while the word and its card
are both on screen, so a card left open at phone width
never swallows Escape after a resize. The `.stage-ui`
overlay has `pointer-events: none`, so `.foot-gist` and the
open disclaimer set it back to `auto`. The first test run
caught this: the word could not be clicked. The foot is
about 70px shorter on phones, so the short-phone rule no
longer needs to touch the disclaimer.

**Verified (small print).** Headless Chrome at the same eight
sizes. On phones, Small print passes a hit test, its card
fits and closes, and nothing overlaps. On tablets and desktop,
the disclaimer is unchanged. The inline script passes
`node --check`. Of 530 tests, 528 pass. The two that fail
are the usage-token tests, which fail only because of a local
`.env` token (17.7).
