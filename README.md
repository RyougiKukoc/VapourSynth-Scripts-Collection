# VapourSynth-Scripts-Collection

`VapourSynth-Scripts-Collection` vendors a curated set of standalone VapourSynth
Python scripts into one VCS-installable distribution while keeping each script
in its own maintenance folder under [`scripts/`](./scripts).

The distribution name is `vs-collection-rk`, so the intended install form is:

```powershell
pip install "vs-collection-rk @ git+https://github.com/RyougiKukoc/VapourSynth-Scripts-Collection.git"
```

The installed runtime keeps the original import names. Existing scripts can keep
using imports such as:

```python
import CSMOD
import fvsfunc
import getfnative
import havsfunc
import kagefunc
import mvsfunc
import muvsfunc
import nnedi3_resample
import nnedi3_rpow2
import sdering_fix
import vsTAAmbk
import yvsfunc
```

## Layout

- `scripts/<name>/` stores the vendored upstream source and `provenance.toml`.
- `scripts/registry.json` is the packaging manifest used by the build hook.
- `src/vs_collection_rk/` exposes a tiny metadata package for introspection.
- `hatch_build.py` stages the bundled scripts into their original import paths
  during wheel builds.

## Bundled Scripts

- `sdering_fix`
- `CSMOD`
- `nnedi3_resample`
- `nnedi3_rpow2`
- `havsfunc`
- `getfnative`
- `mvsfunc`
- `muvsfunc`
- `fvsfunc`
- `vsTAAmbk`
- `kagefunc`
- `yvsfunc`

## Dependency Notes

`vs-collection-rk` installs `VapourSynth`, `vsutil`, and `matplotlib`
automatically, because some bundled modules import them at module import time.

`mvsfunc` is bundled directly inside this collection rather than being pulled as
an external dependency. This keeps `pip install "vs-collection-rk @ git+..."`
self-contained even though upstream `mvsfunc` currently ships a classic
`setup.py` + `requirements.txt` layout and no PyPI distribution was available
during bootstrap.

The collection does not try to normalize runtime plugin requirements. If an
upstream script expects plugins like `fmtc`, `nnedi3`, `znedi3`, `nnedi3cl`,
and so on, those plugin-side requirements still apply.

## Provenance

Each script folder keeps the exact user-specified entry URL plus the canonical
GitHub or gist URL, an upstream revision marker, and any detected license
metadata in `provenance.toml`.

For the scripts collected from user gists, the gist snapshot is preserved as the
authoritative fetch source. If a gist was itself derived from another upstream
repository, that earlier link can be added later without changing the runtime
layout.
