# vendor

Third-party code copied into the published site by `build_site.py`. Nothing here
is modified.

| File | Package | License | Used for |
|---|---|---|---|
| `ufuzzy.min.js` | `@leeoniya/ufuzzy` 1.0.14, `dist/uFuzzy.iife.min.js` | MIT | the search box over the joint list |
| `three/three.module.min.js` | `three` 0.160.0, `build/three.module.min.js` | MIT | the house viewer's scene, geometry and animation |
| `three/addons/loaders/GLTFLoader.js` | `three` 0.160.0, `examples/jsm/loaders/GLTFLoader.js` | MIT | loading `house.glb` |
| `three/addons/controls/OrbitControls.js` | `three` 0.160.0, `examples/jsm/controls/OrbitControls.js` | MIT | orbiting and zooming the house |
| `three/addons/utils/BufferGeometryUtils.js` | `three` 0.160.0, `examples/jsm/utils/BufferGeometryUtils.js` | MIT | GLTFLoader's triangle-mode conversion |
| `three/LICENSE` | `three` 0.160.0 | MIT | the upstream notice |

Downloaded from <https://unpkg.com/@leeoniya/ufuzzy@1.0.14/dist/uFuzzy.iife.min.js>
(7,936 bytes, SHA-256 `5b9e53a8cbbcd95f8e602bdc75e39f6d4d557645f4eb5f7d5c2bbea1edcaaea7`).
`ufuzzy.LICENSE` is the upstream MIT notice, which also ships inside the
minified file's banner. Project: <https://github.com/leeoniya/uFuzzy>.

It is the same library, in the same `filter` → `info` → `sort` order, that
`~/Documents/Dev/wow/converter` uses for its model list. Only the option set
differs: `site_template.html` switches on the library's documented
`unicode: true` regexps so the Japanese names (`金輪`, `腰掛け`) are searchable
too, not just the romanised ones.

## three.js

The house viewer (`tools/house_viewer.js`, published as `docs/house-viewer.js`)
imports `three` and two of its addons through the import map in
`site_template.html`:

```json
{
  "imports": {
    "three": "./vendor/three/three.module.min.js",
    "three/addons/": "./vendor/three/addons/"
  }
}
```

The files are the unmodified r160 release from
<https://unpkg.com/three@0.160.0/>:

| File | Bytes | SHA-256 |
|---|---|---|
| `three.module.min.js` | 670,681 | `3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6` |
| `addons/loaders/GLTFLoader.js` | 108,522 | `d073b438e6a07e1359741dd5d6c76c953420cc0d4fd84eb1bdde94315540e6a3` |
| `addons/controls/OrbitControls.js` | 29,868 | `5a44a9e86a2a0fb11933eed69bc2cd33c76a496854c1aed6ed776efa87d7b064` |
| `addons/utils/BufferGeometryUtils.js` | 31,906 | `9be041e96308775d00e2695cc607645b9a9b64fd7c0e759dd8f7c00a8d92becb` |
| `LICENSE` | 1,081 | the upstream MIT notice |

`copy_vendor()` copies the tree recursively, so the addons keep the relative
paths their own imports expect (`../utils/BufferGeometryUtils.js`). The
`<model-viewer>` specimens still load from Google's CDN and are not vendored;
only the house uses these files.
