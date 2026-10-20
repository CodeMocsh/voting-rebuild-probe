---
version: alpha
name: Vote ballot
description: The current look of the vote screen, read from static/stylesheets/style.css, a byte-for-byte copy of dockersamples-example-voting-app/vote/static/stylesheets/style.css.
colors:
  page: "#F7F8F9"
  heading: "#254356"
  option-a: "#1aaaf8"
  option-a-hover: "#1488c6"
  option-b: "#00cbca"
  option-b-hover: "#00a2a1"
  on-option: "#ffffff"
  tip: "#c0c9ce"
  hostname: "#8f9ea8"
typography:
  option:
    fontFamily: Open Sans
    fontSize: 18px
    fontWeight: 700
    lineHeight: 1.3em
  tip:
    fontFamily: Open Sans
    fontSize: 14px
    fontWeight: 400
  hostname:
    fontFamily: Open Sans
    fontSize: 24px
    fontWeight: 400
  heading:
    fontFamily: Open Sans
    fontSize: 1.17em
    fontWeight: 700
rounded:
  none: 0px
spacing:
  option-gap: 10px
  option-inset: 50px
  tick-inset: 30px
  content-padding: 10px
  content-max-width: 940px
  hostname-bottom: 100px
components:
  option-a:
    backgroundColor: "{colors.option-a}"
    textColor: "{colors.on-option}"
    typography: "{typography.option}"
    rounded: "{rounded.none}"
    width: 330px
    height: 80px
    padding: 0 0 0 50px
  option-a-hover:
    backgroundColor: "{colors.option-a-hover}"
    textColor: "{colors.on-option}"
  option-b:
    backgroundColor: "{colors.option-b}"
    textColor: "{colors.on-option}"
    typography: "{typography.option}"
    rounded: "{rounded.none}"
    width: 330px
    height: 80px
    padding: 0 0 0 50px
  option-b-hover:
    backgroundColor: "{colors.option-b-hover}"
    textColor: "{colors.on-option}"
  heading:
    textColor: "{colors.heading}"
    typography: "{typography.heading}"
  tip:
    textColor: "{colors.tip}"
    typography: "{typography.tip}"
  hostname:
    textColor: "{colors.hostname}"
    typography: "{typography.hostname}"
---

# Vote ballot

## Overview

The ballot is one centred column on a pale grey page: a dark blue heading ("A vs B!"), two
full-colour option buttons, a light tip line, and the container ID near the bottom. The only
source of this look is `static/stylesheets/style.css`, a byte-for-byte copy of
`dockersamples-example-voting-app/vote/static/stylesheets/style.css`. This move keeps the look;
do not change the copy.

`look.html` shows each primitive, marked `data-specimen`, and loads only that stylesheet.
`tests/look/shoot.py` screenshots each one.

## Colors

- **page** `#F7F8F9`: `html` and `body` background.
- **heading** `#254356`: the `h3` in `#content-container-center`.
- **option-a** `#1aaaf8`, hover and focus **option-a-hover** `#1488c6`: `button.a`.
- **option-b** `#00cbca`, hover and focus **option-b-hover** `#00a2a1`: `button.b`.
- **on-option** white: the option label.
- **tip** `#c0c9ce`: `#tip`.
- **hostname** `#8f9ea8`: `#hostname`.

## Typography

One family, Open Sans, weights 400, 600 and 700, imported from Google Fonts. The stylesheet
names no fallback, so with no network the browser's default font shows; the look checks block
outside requests, so their screenshots show that default, not Open Sans.

- **option**: 18px, weight 700, uppercase, left-aligned, in a `#choice` line height of 1.3em.
- **tip**: 14px, left-aligned.
- **hostname**: 24px.
- **heading**: the browser's `h3` default.

## Layout

`#content-container` is a centred table, max width 940px, padding 10px, full height; its
centre cell centres the text. The option buttons stack, 330px by 80px, 10px above and below,
label inset 50px from the left. `#hostname` sits absolutely 100px above the bottom, across the
full width. `#choice` transitions `all 300ms linear`.

## Elevation & Depth

Flat. No shadows. `#content-container` sits at z-index 2 above `#background-stats` at z-index 1.

## Shapes

Square corners everywhere: buttons have radius 0, and `-webkit-appearance` is turned off on
submit buttons. No borders on the options.

## Components

- **Ballot** (`ballot`): the whole screen.
- **Heading** (`heading`): `h3`, "A vs B!".
- **Option A** (`option-a`, `option-a-hover`): `button.a` in `form#choice`.
- **Option B** (`option-b`, `option-b-hover`): `button.b` in `form#choice`.
- **Voted** (`voted-a`, `voted-b`): the chosen button is disabled and gets
  `i.fa.fa-check-circle`, floated right, 30px in, 3px down; the other button gets
  `opacity: 0.5`. The tick is Font Awesome 4.4.0 from a CDN, not this stylesheet; with outside
  requests blocked it shows as an empty space at the right of the chosen button.
- **Tip** (`tip`): `#tip`, "(Tip: you can change your vote)".
- **Hostname** (`hostname`): `#hostname`, "Processed by container ID …".

## Do's and Don'ts

- Do draw the ballot from these tokens and `style.css` only.
- Do keep `style.css` byte-identical to today's; `cmp` checks it.
- Don't read the fallback font or the missing tick in screenshots as the look; the look is Open
  Sans with a Font Awesome tick.
- Don't round the option corners or add shadows.
- Don't add a second stylesheet to `look.html`.
