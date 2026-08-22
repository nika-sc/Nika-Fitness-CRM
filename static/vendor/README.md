# Vendored UI assets

Self-hosted installs run without a CDN. Optional Node.js is a **local CSS build**
(`npm run css`); the compiled file `static/css/nika.build.css` is committed.

| Package | Version | Upstream | License |
| --- | --- | --- | --- |
| Bootstrap Icons | 1.13.1 | https://github.com/twbs/icons | MIT |
| Swiper | 11.2.10 | https://github.com/nolimits4web/swiper | MIT |

Source of the product theme: `static/src/nika.css` (Tailwind v4 + daisyUI v5).
Do not edit `nika.build.css` by hand.

AdminLTE and Bootstrap CSS/JS were removed in the 2026 redesign.
