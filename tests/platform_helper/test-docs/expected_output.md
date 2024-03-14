# Commands Reference

- [cli](#cli)
- [cli hello](#cli-hello)
- [cli argument-replacements](#cli-argument-replacements)
- [cli option-replacements](#cli-option-replacements)

# cli

## Usage

```
cli (hello|argument-replacements|option-replacements) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`argument-replacements` ↪](#cli-argument-replacements)
- [`hello` ↪](#cli-hello)
- [`option-replacements` ↪](#cli-option-replacements)

# cli hello

[↩ Parent](#cli)

## Usage

```
cli hello <name> [--count <count>] 
```

## Arguments

- `name <text>`

## Options

- `--count <integer>` _Defaults to 1._
  - number of greetings
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# cli argument-replacements

[↩ Parent](#cli)

## Usage

```
cli argument-replacements <application> <environment> <service> 
```

## Arguments

- `app <text>`
- `env <text>`
- `svc <text>`

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# cli option-replacements

[↩ Parent](#cli)

## Usage

```
cli option-replacements [--app <application>] [--env <environment>] [--svc <service>] 
```

## Options

- `--app <text>`

- `--env <text>`

- `--svc <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.
