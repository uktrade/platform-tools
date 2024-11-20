# DBT Platform Helper

This package contains a set of tools in the form of a Command Line Interface (CLI) primarily for automating operations used when working with the Department for Business and Trade (DBT) Platform.

## Getting started

To use the Python package `dbt-platform-helper`, follow the steps below.

### Installation

```shell
pip install dbt-platform-helper
```

### Usage

Check `dbt-platform-helper` has installed successfully by executing `platform-helper` in the terminal emulator. You should see an output similar to the following:

```shell
$ platform-helper
Usage: platform-helper [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  bootstrap
  check-cloudformation  Runs the checks passed in the command arguments.
  codebuild
  copilot
  domain
```

Each command can be executed without any arguments or additional commands to present the `help` message.

Below is the output for the `bootstrap` command as of version `0.1.2`.

```shell
$ platform-helper bootstrap --help
Usage: platform-helper bootstrap [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  instructions     Show migration instructions.
  make-config      Generate copilot boilerplate code.
  migrate-secrets  Migrate secrets from your gov paas application to...
```

See the [Commands Reference](https://github.com/uktrade/platform-tools/blob/main/dbt_platform_helper/COMMANDS.md) for a list of all available subcommands.
