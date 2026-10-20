# result: design

This file records the current look of the results screen. The only source is `views/stylesheets/style.css`. That file is a byte-for-byte copy of `dockersamples-example-voting-app/result/views/stylesheets/style.css`. Do not change the copy. This move keeps the look. The result service stays in `dockersamples-example-voting-app/result/`, so this directory holds only the look page, its stylesheet and this file.

`look.html` shows each primitive and loads only that stylesheet. `tests/look/shoot.py` takes one screenshot of each primitive. `look.html` sets `body` opacity to 1, because `app.js` does that on the real screen and does not run here.

## Tokens

### Colour

| Token | Value | Use |
|---|---|---|
| option A | `#2196f3` | `#background-stats-1`, `.choice.cats` text |
| option B | `#00cbca` | `#background-stats-2`, `.choice.dogs` text |
| card | `#fff` | `#choice` background and its 10px side shadows |
| divider | `#C0C9CE` | `.divider` |
| total | `#fff` at opacity 0.5 | `#result` |
| page | browser default | `html`, `body` set no background |

### Type

| Token | Value | Use |
|---|---|---|
| family | `'Open Sans'`, weights 400, 600 and 700, from Google Fonts by `@import` | everything |
| score | 40px, weight 600, line height 1.3em | `#choice` |
| label | uppercase | `.choice .label` |
| total | 45px, weight 600 | `#result` |

The stylesheet names no fallback family. When Google Fonts is not reachable, the browser uses its default font. The look checks block all outside requests, so their screenshots show that default font, not Open Sans.

### Size and spacing

| Token | Value | Use |
|---|---|---|
| card | 450px by 200px, centred | `#choice` |
| choice | 49% of the card, text 50px from the left | `#choice .choice` |
| divider | 2px by 150px, vertically centred | `.divider` |
| total | 40px above the bottom, 20px from the right | `#result` |
| content | max width 940px, padding 10px | `#content-container` |

### Motion

| Token | Value | Use |
|---|---|---|
| page | `all 1s linear`, opacity 0 to 1 when the socket connects | `body` |
| split | `width 400ms ease-in-out` | `#background-stats div` |
| card | `all 300ms linear` | `#choice` |

## Primitives

| Primitive | Markup | `look.html` specimen |
|---|---|---|
| Results | the whole screen | `results` |
| Background split | `#background-stats-1` and `-2`, widths set to the two percentages | `background-split` |
| Score card | `#choice`: `.choice.cats`, `.divider`, `.choice.dogs`, each choice with `.label` and `.stat` | `score-card` |
| Total | `#result`: "No votes yet", "1 vote" or "N votes" | `total-none`, `total-one`, `total-many` |
