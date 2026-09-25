# EXIOM AI — GSAP Animations

Task 9. The client's centrepiece is a brain you zoom into to
reveal the chat. It is built with GSAP 3.15 (core and
Observer), plus a few micro-interactions for the chat.


## 9.1 The brain

A 2D canvas point cloud in the shape of a brain, seen from
the side and swaying slowly in 3D. It is **built from the
network**: every point is a node and every line a link to its
nearest neighbours. Mint pulses walk real paths through that
graph, like signals between service nodes.

* **Shape** (seeded, so it is the same on every visit): two
  cerebral hemispheres with a fissure between them and gyri
  rippled into the surface, the temporal lobes, a cerebellum
  with its fine horizontal folds, and the brainstem.
* **The core:** one hub node on the near hemisphere, linked
  to its eight nearest neighbours, with a heartbeat glow.
  Pulses lean towards it, more so once the dive starts.
* **Cost:** 1,300 nodes on desktop, 1,000 on four-core
  devices and 820 on phones. A frame is one sprite
  `drawImage` per node and pulse, plus three strokes for all
  the links (one per brightness band). Pixel ratio is capped
  at 2 (1.5 on phones). It measured 60 fps in headless Chrome
  with software rendering. The loop runs on `gsap.ticker`, so
  it pauses in a background tab, and it is removed as soon as
  the intro ends.
* **On load:** the nodes condense out of a wide cloud (2.8s)
  while the title lines rise out of their masks. This is the
  page's one orchestrated entrance.


## 9.2 The dive

One paused timeline, in timeline order:

1. The camera flies into the core. A look-at correction
   centres the core by 70% of the zoom, so the chat always
   opens from the middle.
2. The intro copy rises, fades and blurs away, like text the
   camera passes.
3. The core blooms, then the chat opens out of it: a
   `clip-path: circle()` grows from the centre (a CSS
   variable, `--reveal`) while a light overlay (`--flash`)
   clears to the chat.
4. The header, empty state and composer settle in with a
   short stagger.

**Controls.**

* **Scroll (wheel or touch)** scrubs the dive through
  Observer. Input moves a target, and `gsap.quickTo` eases the
  timeline there, so it feels continuous rather than stepped.
  A finger counts for more than a wheel and runs the opposite
  way. Stop scrolling before about 12% and the dive eases back
  to the start. Past 12%, or past 60% while still scrolling,
  it commits and finishes on its own.
* **"Start asking"**, Enter, Space, ↓ and Page Down dive.
* **Escape** and **"Skip intro"** go straight to the chat.

Why Observer rather than ScrollTrigger: the intro is not a
section of a scrolling page. Pinning it to a tall scroll track
would leave the chat below a scroll position. Scrolling up in
the log could then pull the page back into the brain, and the
mobile address bar resizes the track mid-scrub. Observer
gives the same scroll-driven scrub with no page scroll. When
the dive finishes, the stage is hidden and the chat is an
ordinary page.

**While the intro is up,** the chat is `inert`, clipped to
nothing (so it takes no clicks) and the page cannot scroll.

**Going back.** The logo in the chat header ("EXIOM AI, back
to the intro") leads home, as a logo usually does. It plays
the same timeline backwards: the chat folds into the core,
the camera pulls out and the copy returns. Then scrolling and
the button work again. The conversation is kept, so diving
back in returns to it.

* The stage is hidden at the end of a dive, not removed, so
  the timeline can reverse.
* The intro is built on first use. So the logo also works
  after a reload that opened straight into the chat, and the
  brain condenses as the camera pulls out.
* A reload shows wherever the visitor was: the intro if they
  were on it, the chat if they were in it.
* The logo is disabled, and reads as plain text, when the
  intro can't run (reduced motion, no GSAP). After an intro
  failure it is disabled too.
* Skipping during the load animation now completes that
  animation rather than stopping it. Otherwise the title could
  stay half-risen for the next visit home.


## 9.3 Micro-interactions

* **Messages** ease up into place. A non-streamed answer's
  blocks fade in with a short stagger. A typed-out answer
  does not, because it is already on screen.
* **Block height** rolls up to its value over the last few
  thousand blocks, like a counter catching up with the chain.
* **Send button** gives a small elastic press.
* **Thinking** is a signal crossing a three-node synapse, and
  a streaming answer ends in a blinking iris caret. Both are
  CSS.
* **Streaming switch** has a springy thumb. Prompt rows show
  a mint node and indent on hover. Both are CSS transitions.

Every GSAP call goes through `motion()` or `enter()` and clears
its inline styles afterwards.


## 9.4 Failure modes

The intro must never trap anyone behind it.

| Situation | Result |
| --- | --- |
| Reduced motion | No stage (CSS hides it; the script removes it). The chat shows at once, and no animation or loop runs. |
| GSAP or Observer didn't load | Stage removed; the chat works with no motion. |
| No 2D canvas | Stage removed. |
| Reload while in the chat | Stage hidden (`sessionStorage`, try/catch like the other settings). The logo still leads home. |
| Script never ran, or threw early | The stage is visible from the first paint (no chat flash), and a CSS fail-safe fades it out after 8s. The script cancels the fail-safe by adding `is-live`. Verified with JavaScript off. |
| Error while setting up | Caught: stage hidden, logo disabled. |
| Error inside a frame | Caught: loop stopped, skips to the chat, logo disabled. |
| Resize or rotate mid-intro | The canvas resizes; the reveal is centred, so nothing needs rebuilding. |


## 9.5 Delivery

* GSAP 3.15.0 core and Observer are concatenated into
  `static/vendor/gsap-3.15.0.min.js` (83 KB, no source-map
  comments). The file comes from the `gsap` package already in
  `frontend/node_modules`. GSAP is free under its standard
  licence, and the licence header is kept.
* It is loaded with the nonce and versioned like the
  stylesheet (immutable, a year), so there is no third-party
  origin and no change to the CSP.
* The app script is wrapped in a function, so nothing leaks
  onto `window`.


## 9.6 Verified

In headless Chrome (1440×900, and 390×844 with touch):

* the intro renders
* a scroll that stops early settles back
* "Start asking" dives, and frames were checked at 12% speed
* the chat is focused afterwards (mouse only)
* reloading skips the intro
* the logo round trip: back home mid-conversation (messages
  kept), a reload there shows the intro, dive again, a reload
  in the chat shows the chat, and the logo then builds the
  intro on first use; reduced motion disables the logo
* with reduced motion there is no stage
* with JavaScript off, the stage is hidden after 9s
* a mocked stream renders the heading, list, code, link,
  live badge and source, and ends with `aria-busy="false"`

There were no console errors. The only 404 is the favicon,
which the app has never had.
