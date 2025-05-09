# Commands Reference

- [cli](#cli)
    - [cli group-command](#cli-group-command)
        - [cli group-command hello](#cli-group-command-hello)
        - [cli group-command argument-replacements](#cli-group-command-argument-replacements)
        - [cli group-command option-replacements](#cli-group-command-option-replacements)

# cli

## Usage

```
cli group-command 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`group-command` ↪](#cli-group-command)

# cli group-command

[↩ Parent](#cli)

## Usage

```
cli group-command (hello|argument-replacements|option-replacements) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`argument-replacements` ↪](#cli-group-command-argument-replacements)
- [`hello` ↪](#cli-group-command-hello)
- [`option-replacements` ↪](#cli-group-command-option-replacements)

# cli group-command hello

[↩ Parent](#cli-group-command)

## Usage

```
cli group-command hello <name> [--count <count>] 
```

## Arguments

- `name <text>`

## Options

- `--count <integer>` _Defaults to 1._
  - number of greetings
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# cli group-command argument-replacements

[↩ Parent](#cli-group-command)

## Usage

```
cli group-command argument-replacements <application> <environment> <service> 
```

## Arguments

- `app <text>`
- `env <text>`
- `svc <text>`

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# cli group-command option-replacements

[↩ Parent](#cli-group-command)

## Usage

```
cli group-command option-replacements [--app <application>] [--env <environment>] 
                                      [--svc <service>] 
```

## Options

- `--app <text>`

- `--env <text>`

- `--svc <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.
