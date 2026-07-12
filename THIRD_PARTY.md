# Third-Party Sources

This repository is a packaging collection, not a from-scratch codebase. The
actual script sources are vendored under `scripts/<name>/`.

Licensing is mixed:

- `mvsfunc` is vendored as a full upstream package, but the GitHub API did not
  expose an SPDX license identifier for the repository.
- `yvsfunc` includes its upstream `COPYING` file and reports SPDX `WTFPL`.
- The GitHub API did not expose a repository license for several of the
  single-file sources bundled here.
- The user-supplied gists do not carry a separate machine-readable license
  signal through the GitHub gist API.

Before publishing this repository broadly, review each script folder's
`provenance.toml` and any bundled upstream license files to confirm the desired
redistribution posture.

The collection keeps provenance metadata intentionally close to each vendored
script so later license or authorship clarifications can be applied without
guessing where a file came from.

For a repository-level per-script source index, see [`SOURCES.md`](./SOURCES.md).
