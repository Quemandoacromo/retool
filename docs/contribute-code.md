---
hide:
  - footer
---

# Contribute to code

Retool uses [Hatch](https://github.com/pypa/hatch) for environment management, code
formatting and testing. Tests are run using Python 3.10, 3.11, and 3.12.


You can install Hatch and `hatch-pip-compile` with the following command:

```
pip install hatch hatch-pip-compile
```

To enter an environment and install Retool's depedencies, run the following command:

```
hatch shell
```

When you're done and want to exit the environment, run the following command:

```
exit
```

## Run formatters and tests

To run all formatters and tests, run the following command:

```
hatch run all
```

### Formatting and syntax

To only run [`black`](https://github.com/psf/black), [`isort`](https://pycqa.github.io/isort/),
and [`ruff`](https://github.com/astral-sh/ruff) against the code:

```
hatch run style:fix
```

To run MyPy against the code:

```
hatch run types:check
```

### Integration tests

Instead of running the complete test suite, you can run individual tests that validate
specific Retool functionality.

Tests different settings for compilation handling:

```
hatch run integration:compilations
```

Tests that Retool outputs the same content five times in a row:

```
hatch run integration:determinism
```

Tests that Retool is correctly excluding all user-selected title types:

```
hatch run integration:exclusions
```

Tests that Retool is correctly filtering by different language priorities:

```
hatch run integration:languages
```

Tests that Retool is correctly filtering by different region priorities:

```
hatch run integration:regions
```

## Enable developer mode

If you create a file named `.dev` and place it in Retool's folder, the following options
are enabled by default:

* **Output DAT files in legacy parent/clone format**. Useful to ensure file relationships
  are working as they should.

* **Report clone list warnings during processing**. Useful to discover issues with clone
  lists. These are silenced in normal operation, as they can get noisy as DAT files
  update.

* **Pause on clone list warnings**. So you can see what's going on.

You can override this at any time in Retool CLI with the `-q` flag.

## Disable multiprocessing

When using `input` statements in the Python code, make sure to also pass the `--singlecpu`
flag, or turn on **Disable multiprocessor usage** in Retool GUI. This is because `input`
statements don't play well with multiprocessing and cause crashes.


