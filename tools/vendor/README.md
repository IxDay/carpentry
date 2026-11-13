# vendor

Third-party code copied into the published site by `build_site.py`. Nothing here
is modified.

| File | Package | License | Used for |
|---|---|---|---|
| `ufuzzy.min.js` | `@leeoniya/ufuzzy` 1.0.14, `dist/uFuzzy.iife.min.js` | MIT | the search box over the joint list |

Downloaded from <https://unpkg.com/@leeoniya/ufuzzy@1.0.14/dist/uFuzzy.iife.min.js>
(7,936 bytes, SHA-256 `5b9e53a8cbbcd95f8e602bdc75e39f6d4d557645f4eb5f7d5c2bbea1edcaaea7`).
`ufuzzy.LICENSE` is the upstream MIT notice, which also ships inside the
minified file's banner. Project: <https://github.com/leeoniya/uFuzzy>.

It is the same library, in the same `filter` → `info` → `sort` order, that
`~/Documents/Dev/wow/converter` uses for its model list. Only the option set
differs: `site_template.html` switches on the library's documented
`unicode: true` regexps so the Japanese names (`金輪`, `腰掛け`) are searchable
too, not just the romanised ones.
