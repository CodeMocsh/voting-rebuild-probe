# vote: design

This file records the current look of the ballot. The only source is `static/stylesheets/style.css`. That file is a byte-for-byte copy of `dockersamples-example-voting-app/vote/static/stylesheets/style.css`. Do not change the copy. This move keeps the look.

`look.html` shows each primitive and loads only that stylesheet. `tests/look/shoot.py` takes one screenshot of each primitive.

## Tokens

### Colour

| Token | Value | Use |
|---|---|---|
| page | `#F7F8F9` | `html`, `body` background |
| heading | `#254356` | `h3` in `#content-container-center` |
| option A | `#1aaaf8` | `button.a` background |
| option A, hover and focus | `#1488c6` | `#choice button.a:hover`, `:focus` |
| option B | `#00cbca` | `button.b` background |
| option B, hover and focus | `#00a2a1` | `#choice button.b:hover`, `:focus` |
| option text | `white` | `#choice button` |
| tip | `#c0c9ce` | `#tip` |
| hostname | `#8f9ea8` | `#hostname` |

### Type

| Token | Value | Use |
|---|---|---|
| family | `'Open Sans'`, weights 400, 600 and 700, from Google Fonts by `@import` | everything |
| option | 18px, weight 700, uppercase | `#choice button` |
| tip | 14px | `#tip` |
| hostname | 24px | `#hostname` |
| heading | browser default for `h3` | `h3` |
| line height | 1.3em | `#choice` |

The stylesheet names no fallback family. When Google Fonts is not reachable, the browser uses its default font. The look checks block all outside requests, so their screenshots show that default font, not Open Sans.

### Size and spacing

| Token | Value | Use |
|---|---|---|
| option button | 330px by 80px | `#choice button` |
| option gap | 10px above and below | `#choice button` margin |
| option text inset | 50px from the left, left-aligned | `#choice button` |
| tick inset | 30px from the right, 3px down, floats right | `button i` |
| content | max width 940px, padding 10px, centred | `#content-container` |
| hostname | 100px above the bottom of the content | `#hostname` |
| corners | none, radius 0 | `button` |

### Motion

| Token | Value | Use |
|---|---|---|
| choice | `all 300ms linear` | `#choice` |

## Primitives

| Primitive | Markup | `look.html` specimen |
|---|---|---|
| Ballot | the whole screen | `ballot` |
| Heading | `h3`, "A vs B!" | `heading` |
| Option A | `button.a` in `form#choice` | `option-a`, `option-a-hover` |
| Option B | `button.b` in `form#choice` | `option-b`, `option-b-hover` |
| Voted | the chosen button is disabled and gets `i.fa.fa-check-circle`; the other button gets `opacity: 0.5` | `voted-a`, `voted-b` |
| Tip | `#tip`, "(Tip: you can change your vote)" | `tip` |
| Hostname | `#hostname`, "Processed by container ID …" | `hostname` |

The voted tick is the Font Awesome 4.4.0 icon `fa-check-circle`. The template loads it from a CDN, not from this stylesheet. The look checks block that request, so the tick shows as an empty space at the right of the chosen button.
