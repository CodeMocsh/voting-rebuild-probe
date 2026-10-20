---
version: alpha
name: Vote results
description: The current look of the results screen, read from views/stylesheets/style.css, a byte-for-byte copy of dockersamples-example-voting-app/result/views/stylesheets/style.css.
colors:
  option-a: "#2196f3"
  option-b: "#00cbca"
  card: "#ffffff"
  divider: "#C0C9CE"
  total: "#ffffff"
typography:
  score:
    fontFamily: Open Sans
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.3em
  total:
    fontFamily: Open Sans
    fontSize: 45px
    fontWeight: 600
rounded:
  none: 0px
spacing:
  choice-inset: 50px
  card-shadow: 10px
  total-bottom: 40px
  total-right: 20px
  content-padding: 10px
  content-max-width: 940px
components:
  score-card:
    backgroundColor: "{colors.card}"
    typography: "{typography.score}"
    rounded: "{rounded.none}"
    width: 450px
    height: 200px
  choice-a:
    textColor: "{colors.option-a}"
    typography: "{typography.score}"
    padding: 0 0 0 50px
  choice-b:
    textColor: "{colors.option-b}"
    typography: "{typography.score}"
    padding: 0 0 0 50px
  divider:
    backgroundColor: "{colors.divider}"
    width: 2px
    height: 150px
  background-a:
    backgroundColor: "{colors.option-a}"
  background-b:
    backgroundColor: "{colors.option-b}"
  total:
    textColor: "{colors.total}"
    typography: "{typography.total}"
---

# Vote results

## Overview

The results screen fills the window with two colour bands, blue for option A and teal for
option B, their widths the two vote percentages. A white score card sits in the middle, and the
total sits faintly in the bottom right. The only source of this look is
`views/stylesheets/style.css`, a byte-for-byte copy of
`dockersamples-example-voting-app/result/views/stylesheets/style.css`. This move keeps the look;
do not change the copy. The result service stays in `dockersamples-example-voting-app/result/`,
so this directory holds only the look page, its stylesheet and this file.

`look.html` shows each primitive, marked `data-specimen`, and loads only that stylesheet. It sets
`body` opacity to 1, because `app.js` does that on the real screen and does not run here.
`tests/look/shoot.py` screenshots each specimen.

## Colors

- **option-a** `#2196f3`: `#background-stats-1` and `.choice.cats` text.
- **option-b** `#00cbca`: `#background-stats-2` and `.choice.dogs` text.
- **card** `#fff`: `#choice` background and its side shadows.
- **divider** `#C0C9CE`: `.divider`.
- **total** `#fff` at opacity 0.5: `#result`.
- The page itself sets no background; the bands cover it.

## Typography

One family, Open Sans, weights 400, 600 and 700, imported from Google Fonts. The stylesheet
names no fallback, so with no network the browser's default font shows; the look checks block
outside requests, so their screenshots show that default, not Open Sans.

- **score**: 40px, weight 600, line height 1.3em; `.label` is uppercase.
- **total**: 45px, weight 600.

## Layout

`#background-stats` covers the window; its two divs are inline blocks, 50% each by default,
their widths set to the percentages, transitioning `width 400ms ease-in-out`.
`#content-container` is a centred table, max width 940px, padding 10px, full height; its centre
cell centres the card both ways. Each choice takes 49% of the card, vertically centred, text
inset 50px; A floats left, B floats right, the divider floats between, vertically centred.
`#result` sits 40px from the bottom and 20px from the right. `body` fades in with
`all 1s linear` when the socket connects; the card transitions `all 300ms linear`.

## Elevation & Depth

Three layers by z-index: the bands at 1, the content at 2, the total at 3. The card's only
shadow is a flat white `10px 0 0` on each side, which widens it rather than lifting it.

## Shapes

Square corners. The card is a 450px by 200px rectangle; the divider a 2px by 150px rule.

## Components

- **Results** (`results`): the whole screen.
- **Background split** (`background-split`): `#background-stats-1` and `-2`, here at 70/30.
- **Score card** (`score-card`): `#choice` holding `.choice.cats`, `.divider`, `.choice.dogs`,
  each choice with `.label` and `.stat`.
- **Total** (`total-none`, `total-one`, `total-many`): `#result`, "No votes yet", "1 vote" or
  "N votes".

## Do's and Don'ts

- Do draw the results screen from these tokens and `style.css` only.
- Do keep `style.css` byte-identical to today's; `cmp` checks it.
- Don't read the fallback font in screenshots as the look; the look is Open Sans.
- Don't give the card rounded corners or a lifting shadow.
- Don't add a second stylesheet to `look.html`.
