# Sharing conduits as packages

A conduit is just a folder, so conduits are shareable. `atelier add` installs
them from a git repo or a local path.

```bash
atelier add owner/repo                       # GitHub shorthand
atelier add https://github.com/owner/repo.git
atelier add ./some/local/package
atelier add owner/repo --ref v1.2.0          # pin a branch, tag, or commit
```

> **Conduits are code.** A conduit can run any shell command on your machine the
> moment you `atelier run` it. Read a package before you install it, and pin
> `--ref` for anything you do not control.

## Package layout

Any repo with its conduits under `.atelier/conduits/` and an
`atelier-package.yaml` at the root:

```yaml
name: my-conduits        # letters, digits, _ and - only
version: 1
conduits:
  - deploy
  - nightly_report
```

Each listed name must be a directory under `.atelier/conduits/`. The **whole
directory is copied**, so helper scripts, templates and reference files next to
`conduit.yaml` travel with it. That is what makes `{{conduit_dir}}` the right way
to reach them - an absolute path baked into the YAML would break on install.

Without a manifest, flow-atelier discovers conduits by scanning
`.atelier/conduits/` and warns that it did so. Prefer the manifest: it is the
only way to ship a subset.

**Schedules are never installed.** They hold machine-specific state (`run_path`,
absolute paths, timezones), so a package can ship example schedule files but the
user has to edit and `atelier schedule add` them.

## Install target

```bash
atelier add owner/repo --project      # into ./.atelier (this project only)
atelier add owner/repo --no-project   # into ~/.atelier (every project)
```

Omit both and you are asked. Global is the usual choice for a package you want to
run from anywhere; project-local wins on name collision at run time.

## Collision behavior

An existing conduit of the same name is **skipped, not overwritten**, unless you
pass `--force`. This is the rule that makes re-running `atelier add` after a new
release a no-op - it does not upgrade anything.

To actually upgrade:

```bash
atelier update <package>              # re-fetch from the recorded source, re-install
atelier update <package> --force      # and overwrite colliding conduits
atelier add <source> --force          # equivalent, naming the source again
```

## Uninstall

```bash
atelier remove <package>
```

Deletes only the conduits that **install actually wrote**. A conduit that was
skipped on collision - because you already had one by that name - is left alone.

## Authoring a package

1. Put each conduit in `.atelier/conduits/<name>/conduit.yaml`.
2. Keep helper scripts beside the conduit and reach them with `{{conduit_dir}}`.
3. Write `atelier-package.yaml` listing exactly the conduits you mean to ship.
4. Prefer pure-stdlib helpers over ones needing a package manager - a helper that
   needs `uv` or `npm` adds a dependency the installing user did not choose.
5. Declare every input with a description, and give optional ones a `default` so
   a bare `atelier run` does something sensible.
6. Ship example schedule files under `.atelier/schedules/` and say in your README
   that they are examples, not installed state.
7. Test with `atelier check` and `atelier plan` before publishing - both run no
   tasks.

Cross-conduit references inside one package work through the shared conduits
directory. A conduit reaching a sibling's scripts uses
`{{conduit_dir}}/../<sibling>/scripts/...`, which holds because the whole package
installs into one conduits directory. That coupling is worth a comment in the
YAML, since it breaks if the conduits are ever installed separately.
