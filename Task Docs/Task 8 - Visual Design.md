# EXIOM AI — Visual Design

Task 8. A production redesign of the chat page
(`templates/index.html`, `static/style.css`). The motion is
Task 9. The chat's behaviour (streaming, the typing reveal,
following, formatting, errors, privacy notice) is unchanged.

Tests: 528, all passing (with `EXIOM_USAGE_TOKEN` unset; see
8.6).


## 8.1 Direction

The brief: tech-savvy users; modern, sleek, amazing. The
subject is a privacy coin secured by service nodes, with an
AI that answers questions about it. So the one idea is **the
network as a mind**. The intro brain is drawn from nodes and
links (Task 9), and the chat is what you find inside it.
Everything else stays quiet so that moment carries the page.

**Colour.** A deep indigo field with two signals, each with
one job:

| Token | Hex | Used for |
| --- | --- | --- |
| Deep field | `#060A1F` | Background (clearly blue, not a tinted black) |
| Raised | `#0C1331` | Composer |
| Ink | `#EEF1FF` | Text, primary buttons |
| Muted | `#8E97C4` | Secondary text (≈6.5:1 on Deep field) |
| Iris | `#8B9CFF` | The mind: EXIOM AI, links, list markers, neurons |
| Mint | `#5DF2D0` | Only what is live: the chain, pulses, the core, focus rings |

**Type.** One family, **Mona Sans** (OFL), used across its
width axis: expanded (`font-stretch: 125%`, weight 300) for
the display lines, normal for reading. Chat text is 16px /
1.6. Lines are held under ~75 characters by a 46rem column.

**Naming.** The assistant is called "EXIOM AI" everywhere, as
the backend and its error messages already call it. The old
page mixed in "XEQM AI". The product stays "XEQM Hub".


## 8.2 Layout

The chat is a full-height app (`100dvh`): a header bar, a
scrolling log and a docked composer.

* **Header:** the mark (a ring with a mint core, the node you
  dive into), "EXIOM AI", a live block chip that links to the
  Explorer, and the streaming switch.
* **Empty state:** "What do you want to know?" in expanded
  type, a one-line lede, and the four suggestions as plain
  rows divided by hairlines (two columns on wide screens). No
  cards, icons or arrows. The rows are questions, not a
  sequence, so they are not numbered.
* **Messages:** the user's question is a right-aligned iris
  bubble. EXIOM AI's answer is unboxed text under a small
  header, where the "Live Explorer data" badge sits. The
  source line is set off by a hairline.
* **Composer:** now a `textarea` that grows to 180px. Enter
  sends, Shift+Enter adds a line, and nothing is sent while an
  input method (CJK) is still composing. The send button is an
  icon with the accessible name "Ask".
* **Privacy notice (Task 13):** unchanged wording, under the
  composer.


## 8.3 Desktop

The column is centred at 46rem, with the log's padding
computed from the viewport so the scrollbar stays at the
window's edge. The intro puts the copy bottom-left and the
brain right of centre.


## 8.4 Mobile

* The intro stacks the brain above the copy, and "Start
  asking" becomes full width. Under 400px the block chip
  leaves the intro bar, because it is still in the chat
  header.
* `viewport-fit=cover` with `env(safe-area-inset-*)` padding
  keeps the bar and composer clear of notches and the home
  indicator.
* The composer text is 16px, so iOS does not zoom on focus.
* The streaming label hides; the switch keeps its accessible
  name.
* After the intro, only a mouse user gets the composer
  focused, so an uninvited touch keyboard never covers the
  chat.


## 8.5 Accessibility

* A visible mint focus ring on everything, including the
  switch.
* The log is `role="log"` and focusable (keyboard scrolling
  already stopped the follow). While an answer types out, its
  message is `aria-busy="true"`, so a screen reader reads the
  finished answer rather than every frame.
* The user's messages carry a hidden "You:" prefix.
* `prefers-reduced-motion`: no intro, no loops, no
  transitions (Task 9).


## 8.6 Security and tests

* The CSP is unchanged: `font-src 'self'`, `script-src` nonce
  only. So the font is **self-hosted**
  (`static/fonts/mona-sans-latin-wdth.woff2`, Latin, variable
  width and weight, 98 KB, with its OFL licence alongside). It
  is preloaded, and referenced with `?v=5.3.0` so the existing
  versioned-asset rule caches it for a year.
* `test_page_carries_a_nonce_csp_that_matches_its_only_script`
  now expects two scripts: the inline app and the GSAP file.
  Both must carry the response's nonce, and neither may come
  from another origin. The `security.py` comment says the same.
* No inline handlers and no `style` attributes. Heights and
  animations are set through the CSSOM, which `style-src
  'self'` allows.
* `usage.html` shares the shell (tokens, font, bar, mark), and
  `usage.css` now uses the tokens.
* **Pre-existing:** `test_usage_endpoint_is_off_without_a_token`
  and `test_usage_page_is_off_without_a_token` fail when the
  local `.env` sets `EXIOM_USAGE_TOKEN`, because it leaks into
  the test app. They fail the same way before this task. With
  it unset, all 528 pass.
