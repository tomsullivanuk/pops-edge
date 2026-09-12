# Pops’ Edge NFL brand implementation

## Reference and scope

The Product Owner requested application of the shared [brand sheet](https://chatgpt.com/s/p_2d47be53770481919cb577cd69c9e0a9) and [NFL dashboard mockup](https://chatgpt.com/s/p_aa5d73ba18848191bc5739be11fba891). These links expose image posts, not full conversation histories. This document records the guidance visible in those images and the implementation choices made from it.

The Product Owner approved the implemented preview on September 12, 2026.
These requirements govern visual identity; methodology and product semantics
retain their existing authority.

## Visual principles

- Deep Navy `#0B2341`: wordmark, primary button, table headers.
- Edge Green `#18A85B`: monogram accent, active tab indicator, completed status dot.
- Dark green `#087440`: readable positive values and focus outlines on white.
- White surfaces, cool pale-gray surroundings, thin borders, restrained shadows.
- Bold wordmark with a slanted navy/green PE symbol; compact sport and version labels.
- Pale-green contract chips; negative numbers retain muted red and warnings retain amber. Text and numeric signs continue to communicate meaning without color alone.
- System fonts avoid remote downloads. The exact typeface was not established from the shared images.

`nfl_brand.py` contains the shared CSS and an editable SVG adaptation of the reference monogram. It is a reconstruction for this application, not the original master artwork. Replace it with the original vector if supplied. The mark is decorative beside the accessible wordmark. The brand sheet also shows dark and monochrome variants; those remain future assets because the current application uses a light theme.

## Application boundaries

Preserve the two functional tabs, filters, sorting, source notes, refresh progress and keyboard behavior. The mockup's additional navigation does not establish new product features. Embed assets into rendered HTML so saved sheets remain portable and make no external font or image requests.

Must hold: branding is presentation only; probabilities, prices, fees, wagers, capture rules and research evidence are unchanged. Accepted limitation: the logo is a vector adaptation. Deferred: other sports, dark mode, new navigation and original-master asset replacement.
