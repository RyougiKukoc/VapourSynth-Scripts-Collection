# Script Sources

This document is the repository-level provenance index for every vendored
script in `VapourSynth-Scripts-Collection`.

Each entry intentionally distinguishes between:

- `Requested source`: the exact URL that was requested during collection.
- `Canonical upstream`: the repository or gist currently treated as the
  authoritative upstream for future maintenance.

Each `scripts/<name>/` folder also keeps a local `provenance.toml` with the
same source data next to the vendored runtime files.

## Source Index

| Folder | Import | Kind | Requested source | Canonical upstream | Revision |
| --- | --- | --- | --- | --- | --- |
| [`sdering_fix`](./scripts/sdering_fix/) | `sdering_fix` | `gist` | <https://gist.github.com/RyougiKukoc/c3832d96a8dce6f609f6e29888af94a6> | <https://gist.github.com/RyougiKukoc/c3832d96a8dce6f609f6e29888af94a6> | `257d981098f67479bf029acda0fdeffa7c38ee08` |
| [`CSMOD`](./scripts/CSMOD/) | `CSMOD` | `github-file` | <https://github.com/fdar0536/VapourSynth-Contra-Sharpen-mod/blob/master/CSMOD.py> | <https://github.com/fdar0536/VapourSynth-Contra-Sharpen-mod> | `b9ff7253bf217dded071b88fb8a6d212aceb81f4` |
| [`nnedi3_resample`](./scripts/nnedi3_resample/) | `nnedi3_resample` | `github-file` | <https://github.com/HomeOfVapourSynthEvolution/nnedi3_resample/blob/master/nnedi3_resample.py> | <https://github.com/HomeOfVapourSynthEvolution/nnedi3_resample> | `314c6446a65c2e25fd7a997051b09830f361675e` |
| [`nnedi3_rpow2`](./scripts/nnedi3_rpow2/) | `nnedi3_rpow2` | `gist` | <https://gist.github.com/RyougiKukoc/6c9225aa3f010ef65d341cc5f770cf23> | <https://gist.github.com/RyougiKukoc/6c9225aa3f010ef65d341cc5f770cf23> | `4e6c2fac9d3159f1f1c93e2a92d492ce7b69b1b3` |
| [`havsfunc`](./scripts/havsfunc/) | `havsfunc` | `gist` | <https://gist.github.com/RyougiKukoc/ea451bd51d0dc33ba5e0c4d5566653cf> | <https://gist.github.com/RyougiKukoc/ea451bd51d0dc33ba5e0c4d5566653cf> | `4e0d21258869283ce04568dda0173e4c8b890668` |
| [`getfnative`](./scripts/getfnative/) | `getfnative` | `github-file` | <https://github.com/YomikoR/GetFnative/blob/main/getfnative.py> | <https://github.com/YomikoR/GetFnative> | `9edcd58346fbffa46f6735637f91ae24dfabcb74` |
| [`mvsfunc`](./scripts/mvsfunc/) | `mvsfunc` | `github-package` | <https://github.com/HomeOfVapourSynthEvolution/mvsfunc> | <https://github.com/HomeOfVapourSynthEvolution/mvsfunc> | `865c7486ca860d323754ec4774bc4cca540a7076` |
| [`muvsfunc`](./scripts/muvsfunc/) | `muvsfunc` | `github-file` | <https://github.com/WolframRhodium/muvsfunc/blob/master/muvsfunc.py> | <https://github.com/WolframRhodium/muvsfunc> | `d278cd3a68250a4d9562c6ec2b401f1a76c324a3` |
| [`fvsfunc`](./scripts/fvsfunc/) | `fvsfunc` | `github-file` | <https://github.com/Irrational-Encoding-Wizardry/fvsfunc/blob/master/fvsfunc.py> | <https://github.com/Irrational-Encoding-Wizardry/fvsfunc> | `076dbde68227f6cca91304a447b2a02b0e95413e` |
| [`TAAmbk`](./scripts/TAAmbk/) | `vsTAAmbk` | `github-file` | <https://github.com/HomeOfVapourSynthEvolution/vsTAAmbk/blob/master/vsTAAmbk.py> | <https://github.com/HomeOfVapourSynthEvolution/vsTAAmbk> | `fef19f85c96c0d7e281627942c358ee1b92d7dbe` |
| [`kagefunc`](./scripts/kagefunc/) | `kagefunc` | `github-file` | <https://github.com/Irrational-Encoding-Wizardry/kagefunc/blob/master/kagefunc.py> | <https://github.com/Irrational-Encoding-Wizardry/kagefunc> | `96947a1bda5639a4e0b89202e964a15bc337521d` |
| [`yvsfunc`](./scripts/yvsfunc/) | `yvsfunc` | `github-package` | <https://github.com/RyougiKukoc/yvsfunc-with-toml.git> | <https://github.com/RyougiKukoc/yvsfunc-vcs> | `ee3309efe2543c6680619f6deb64496102e7eb64` |

## Maintenance Notes

### Gist-backed snapshots

- `sdering_fix`, `nnedi3_rpow2`, and `havsfunc` are currently vendored from
  user-supplied gist snapshots.
- If any of those gists are later confirmed to be derived from an earlier
  GitHub repository or another gist, add that earlier upstream to the local
  `provenance.toml` rather than replacing the current gist record.

### Full vendored packages

- `mvsfunc` is vendored as a full package because several bundled scripts import
  it directly, and relying on a separate external install would make
  `pip install "vs-collection-rk @ git+..."` less reliable.
- `yvsfunc` is also vendored as a full package. The originally requested URL and
  the current canonical repository differ, so both links are kept on record.

## Where To Update Provenance

When a vendored script is refreshed, update all three places together:

1. `scripts/<name>/provenance.toml`
2. `scripts/registry.json`
3. This `SOURCES.md` index
