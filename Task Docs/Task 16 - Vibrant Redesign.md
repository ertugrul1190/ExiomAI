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

## 16.11 Revision: signal fire again, and a cleaner landing

The client's fourth round asked for eight changes.

**Palette.** "Signal fire" (16.6) is back: black `#020409`,
blue `#3D8BFF`, orange `#FF7A1A`, amber `#FFB23F` and ice
`#8FE6FF`, with the 16.6 values for `--raised`, `--ink` and
`--muted`. Everything 16.9 renamed is renamed back: `--teal`
→ `--blue`, `--aqua` → `--ice`, `TEAL` → `BLUE`, `AQUA` →
`ICE`, `data-tone="teal"`/`"aqua"` → `"blue"`/`"ice"`.
`--deep-rgb` and `--ink-rgb` (from 16.9) stay, with the new
values. `--cool` is deleted. The components that 16.9 moved
off orange go back to their 16.6 look:

* **Start chatting:** a `--hot` face with `--on-hot` text, an
  orange glow, and a wheel of orange, amber, ice and blue. The
  mouth has an amber lip and an ice core.
* **Xrypto play button:** orange edge, fill and ripple, amber
  name, and a `--hot` disc.
* **Question bar:** a blue → orange → amber edge, with an
  orange halo on focus. The teal caret and selection rules are
  gone. The send button stays orange.
* **Your messages:** a blue bubble (`#2563EB` → `#1B3FA8`) with
  white text.
* `theme-color` is `#020409` on both pages.

These keep their later changes and only change colour: the
single status line and its orange chip (chat only now), the
Xrypto links as pills (now blue), and the Feedback and
Support cards.

**Top bar.** The landing's top left is the logo alone, at
36px, with `alt="ExiomAI"`. The chat bar is the same, and
its button still says "ExiomAI, back to the intro" to screen
readers. The landing's status chip is gone. **Buy XEQM**
takes its place at the top right, as a blue glass pill (40px,
blue edge and wash, ink text).

**The name.** ExiomAI is bigger (`--title-size` is now
`clamp(3.25rem, min(9vw, 14vh), 9.5rem)`) and weight 900. Its
colours move slowly through the palette: ink, pale blue, blue,
orange, amber and back. This is a 250% gradient clipped to the
text, animated by `background-position` over 9 seconds,
alternating. A blurred blue and orange light (`.stage-title::after`)
sits behind it. "Welcome to" is plain ink. The chat's
"What do you want to know?" keeps the static 16.6 gradient.

**By Xrypto.** The "Click here" tag is removed, along with its
CSS and the `nudge` keyframes. The line is smaller: 0.9375rem,
a 22px play disc and tighter padding.

**The lede.** It is smaller (`clamp(0.9375rem, 1.05vw,
1.0625rem)`) and closer to the name: the gap under the title
went from 20px to 10px, and under "by Xrypto" from 28px to
14px. The client wanted it "readable but not too boring or too
dull". It is a light blue-white `#C9D6EC` rather than muted,
and "No question is too small." is amber. It uses
`text-wrap: pretty`, so no word sits alone on a line.

**The arrow.** "Or scroll to dive in" is gone. In its place is
a round blue arrow (`#stageDown`), centred directly under Start
chatting. `.stage-actions` is now a column that centres its
items. The arrow inside the circle sinks gently. Clicking it
dives, the same as Start chatting. It is `tabindex="-1"` and
`aria-hidden`, because keyboards and screen readers already
have Start chatting and ArrowDown. On phones it is 38px and
scrolls down to the foot instead (16.12). A first pass centred
it on the screen above the foot; the client asked for it under
the button.

**Feedback and Support** now sit on Xrypto's line, just after
its links (`.link-line` wraps the Xrypto row and `.foot-asks`).
The foot is one column, and the Official EXIOM row sits under
that line. On wide screens a card ends at its word. From 900px
down, the words may wrap under the links, so the cards open
from the line's left edge, where they always fit. Phones keep
the 16.10 icon strip, with the words centred under it: both
link groups fill the phone's width, so there is no room left on
the line.

**Verified.** Headless Chrome over CDP at 1440×900, 1366×768,
1024×680, 820×1180, 600×900, 390×844, 375×667 and 320×568.
Nothing overlaps, nothing scrolls sideways, and nothing is
off screen. The arrow and Buy XEQM pass a hit test. On
tablets and desktop, Feedback and Support share the Xrypto
line. Every card fits the viewport. Clicking the arrow dives into the chat, which draws
in the restored palette. There were no console errors, and the
inline script passes `node --check`. No teal or aqua values or
names are left in `static/` or `templates/` (grep). Of 530
tests, 528 pass. The two that fail are the usage-token tests,
which fail only because of a local `.env` token (17.7).

## 16.12 Phones: a clean first screen

The client found the phone landing cluttered: the link strip,
Feedback and Support, and the small print all sat under Start
chatting. They asked for that part to move "into a scrolled
down page" on mobile.

**Two parts.** At 600px or narrower, `.stage-ui` becomes a
vertical scroll box (`overflow: hidden auto`, `overscroll-behavior:
contain`, no scrollbar). A new `.stage-hero` wraps the top bar,
the copy and the arrow. On phones it is at least one screen
tall (`min-height: 100%`), so the first screen shows only the
logo, Buy XEQM, the name, the lede, Start chatting and the
arrow. The foot starts exactly at the bottom edge, a scroll
below. It has its own dark ground (`--deep`, fading in from
92%) and runs edge to edge. On wider screens `.stage-hero` is
`display: contents`, so tablets and desktop are unchanged.

**Scrolling only scrolls on phones.** A swipe on the landing
used to scrub the dive, so the page could not scroll. On phones
the dive's `Observer` does not exist at all, so no wheel,
trackpad or touch input scrubs the dive there. A first pass kept
wheel-to-dive on phones. The client saw a scroll both dive and
scroll the page (a wheel or trackpad in a narrow window), so it
was removed. The observer is rebuilt whenever the layout
crosses 600px (`phoneLayout`, a `matchMedia`). `listen()`
remembers whether the dive is armed, so a rebuilt observer
comes back in the right state. Crossing into the phone layout
mid-scrub settles the dive back. `.stage` and `.stage-ui` allow
`touch-action: pan-y` there. Start chatting still dives, as do
Enter, Space and the arrow keys. On phones the arrow scrolls
smoothly down to the foot. Returning from the chat resets the
scroll to the top. Tablets and desktop still dive on a swipe
or scroll.

**The foot on phones** keeps the 16.10 icon strip, with
Feedback and Support centred under it. With a whole part of
the page to itself, the small print now shows in full, so the
one-line gist and its **Small print** card (16.10) are
removed: the markup, the CSS and the Escape special case in
the script's comment. The rule that dropped the lede on phones
shorter than 800px is gone too, because the lede now fits
down to 320×568. The heading's glow is kept inside the width
on phones, so the scroll box never scrolls sideways.

**Verified.** Headless Chrome over CDP at 390×844, 375×667,
360×740, 320×568 and 600×900 (touch). The first screen holds
the name, lede, Start chatting, the arrow and Buy XEQM. The
foot starts at the bottom edge, and nothing scrolls sideways.
A synthesized touch swipe and a mouse wheel each scroll the
page (about 290px) without diving. A desktop window narrowed to
phone width does the same. The arrow brings the whole foot, small print
included, into view. Feedback passes a hit test there, and
both cards fit. Start chatting still dives on phones. At 1440×900 a
wheel dives, and at 820×1180 a touch swipe dives, as before.
(The test clears `sessionStorage` before each load, because
after a dive the intro is skipped on reload.) At 820×1180,
1024×680, 1366×768 and 1440×900 the arrow is centred under
Start chatting and the layout is as in 16.11. There were no console errors, and the inline
script passes `node --check`. Of 530 tests, 528 pass. The two
that fail are the usage-token tests, which fail only because
of a local `.env` token (17.7).


## 16.13 The new logo

The client's `static/newlogo.png` (1254px) is now the source in
place of `logo.png`. It is a brain and robot face in a speech
bubble, circled by an orbit, over the "ExiomAI" wordmark. The
wordmark can't be read at 30 to 36px, so the served files
are cut from the mark alone: the image above the wordmark
(rows 0 to 955), trimmed to its content and padded to a
transparent square. From that square, Pillow writes
`logo-128.png`, `favicon-32.png` and `apple-touch-icon.png` at
the same names and sizes as before. The templates don't change,
and `asset_version` busts the caches. The mark isn't round, so
`.brand-mark` loses its `border-radius: 50%`, which would clip
the orbit's ends. `logo.png` is left in `static/` but nothing uses
it.

**Revision: the full logo.** The client wants the wordmark
kept. The brand mark is now `logo-full.png`: the whole logo,
trimmed and padded to a transparent square, 192px (4× the
largest display size). It grew from 36 to 48px on the landing
and in the chat bar, and from 30 to 40px on the usage page.
The favicons stay cut from the mark alone, because at 32px the
wordmark is a smudge. `logo-128.png` is no longer used.

**The name's font.** The logo's wordmark looks AI-drawn, so
it has no exact font. Its letterforms (the rounded, open "E"
with a slanted bar, the crossbar-less "Λ" A) are closest to
Nasalization (Typodermic), which isn't on Google Fonts. Of the
free fonts, Audiowide (OFL) is the nearest; Michroma and Orbitron
were compared and are further off. The landing's "ExiomAI" line
(not "Welcome to") is now set in Audiowide, self-hosted as
`fonts/audiowide-latin.woff2` (latin subset, 14 KB, with
`OFL-audiowide.txt`) because the CSP allows only `font-src
'self'`, and preloaded like Mona Sans. It is set at weight 400
with no negative tracking, because Audiowide has a single weight
and its letters touch when tracked in. The colour flow and glow are unchanged.

**Verified.** Headless Chrome over CDP at 1440×900 and 390×844.
The name renders in Audiowide (`document.fonts.check`), 720px
and 358px wide, with no sideways scroll. The full logo reads at
48px in the top bar.


## 16.14 Phones: the chat's small print and the keyboard

Two things the client found on phones.

**The privacy note was a paragraph.** Under the composer it
ran to five lines on a phone. At 600px or narrower it now folds
to one line, "AI answers can be wrong. Not financial advice.",
and a **Small print** word. This is the landing's old pattern
(16.10, since retired there). The word is an `.ask-toggle` on
the same wiring as Feedback and Support. It opens the real
`#privacyNote` (every word, never duplicated, still the
textarea's `aria-describedby`) as a card above the composer.
Clicking outside, Escape or opening another card closes it.
Wider screens show the note in full, as before, and never
show the line.

**The keyboard opened by itself.** After every answer the
send function's `finally` put the focus back in the input. On
a phone that pops the keyboard over the answer just written.
It now refocuses only when `(pointer: fine)` matches, the same
rule the intro's hand-off to the chat already used (Task 17).
A mouse user can still type the next question straight away.

**Verified.** Headless Chrome over CDP. At 390×844 with touch
and a coarse pointer, the line is one row (28px) with no
sideways scroll. Small print opens the card at 16 to 374px
above the composer, and an outside click closes it. After
asking "who are you", nothing holds the focus. At 1440×900
with a fine pointer, the note shows in full, the line is
hidden, and the focus returns to the input after the answer.
Of 530 tests, 528 pass. The two that fail are the usage-token
tests, which fail only because of a local `.env` token (17.7).


## 16.15 Phones: chat messages a step smaller

The client found the chat "zoomed in" on phones. The messages
inherited the page's 16px at a 1.6 line height, with 28px
between messages and roomy bubbles, so a 390px screen held
about 38 characters a line. At 600px or narrower, messages are
now 14px at 1.55, 18px apart. The user's bubble is tighter
(8px 13px padding, 17px corners). Paragraph gaps are 0.6em,
and the headings are scaled to match (h2 19px, h3 17px, h4 the
body size). A line now holds about 45 characters. The textarea
stays at 16px, because under that iOS zooms the page when it is
focused. Tablets and desktop are unchanged.

**Verified.** Headless Chrome over CDP. At 390×844 the answer
and bubble compute to 14px and the textarea to 16px. The
identity answer takes four lines instead of six. At 1440×900
both are still 16px. Of 530 tests, 528 pass. The two that fail
are the usage-token tests, which fail only because of a local
`.env` token (17.7).


## 16.16 The logo over the "m"

**The logo, without the name.** The brand mark is the mark
alone again (16.13), as `logo-mark.png`: `newlogo.png` above
the wordmark (rows 0 to 953; the wordmark's first row is 954),
trimmed where the alpha passes 24 so faint glow doesn't pad it,
centred on a transparent square and written at 384px by Pillow.
It is back to 36px in the chat bar and 30px on the usage page.
`logo-full.png` and `logo-128.png` stay in `static/` but
nothing uses them. The favicons are unchanged.

**The top bar has no logo.** It holds only Buy XEQM, kept at
the right (`justify-content: flex-end`). Phones hid the bar
for one round; the client wanted Buy XEQM back.

**The logo floats over the "m".** "Welcome to ExiomAI" stays.
The "m" is wrapped in `.title-m`, and the mark is positioned
inside it: centred on the letter, 0.54em square (up from
0.46em, as the client asked for it a tad bigger), its bottom
0.9em above the letter's box, just clear of the "m". It has
no animation of its own. It is inside the name, so it rises
with it on load. The name's line needed `overflow: hidden` to
clip the rise, which would have cut the mark off. It now uses
`clip-path: inset(-1em -1em 0)`, which clips only the bottom
edge. The mark has `alt=""`, so the heading still reads
"Welcome to ExiomAI".

**The lede.** "Your AI assistant for all things EXIOM: clear,
simple answers whenever you need them." The amber "No question
is too small." now has a line of its own.

**Phones: the brain moves.** The brain's centre on portrait phones moved from 50% to 46% across and
from 26% to 29% down (Task 17, 17.10).

**Tried and reverted.** The logo beside the name in place of
"Welcome to", the arrow centred on the page, and phone copy
raised with the arrow halfway between Start chatting and the
screen's bottom edge. The client preferred the heading, arrow
and phone spacing as they were.

**Verified.** Headless Chrome over CDP at 1440×900, 1280×720,
820×1180, 390×844, 375×667 and 320×568: no sideways scroll,
and the mark sits over the "m" with nothing clipped (68px on
desktop, 28px on a 390px phone), clear of "to". Buy XEQM shows
at every size, and the brain clears it on phones. The arrow still dives, and the chat bar shows the 36px
mark. Of 530 tests, 528 pass. The two that fail are the
usage-token tests, which fail only because of a local `.env`
token (17.7).
