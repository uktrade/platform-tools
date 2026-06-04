# Commands Reference

- [cli](#cli)
    - [cli great-greets](#cli-great-greets)
        - [cli great-greets hello](#cli-great-greets-hello)
        - [cli great-greets argument-replacements](#cli-great-greets-argument-replacements)
        - [cli great-greets option-replacements](#cli-great-greets-option-replacements)

# cli

## Usage

```
cli great-greets 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`great-greets` ↪](#cli-great-greets)

# cli great-greets

[↩ Parent](#cli)

## Usage

```
cli great-greets (hello|argument-replacements|option-replacements) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`argument-replacements` ↪](#cli-great-greets-argument-replacements)
- [`hello` ↪](#cli-great-greets-hello)
- [`option-replacements` ↪](#cli-great-greets-option-replacements)

# cli great-greets hello

[↩ Parent](#cli-great-greets)

## Usage

```
cli great-greets hello <name> [--count <count>] 
```

## Arguments

- `name <text>`

## Options

- `--count <integer>` _Defaults to 1._
  - number of greetings
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# cli great-greets argument-replacements

[↩ Parent](#cli-great-greets)

## Usage

```
cli great-greets argument-replacements <application> <environment> <service> 
```

## Arguments

- `app <text>`
- `env <text>`
- `svc <text>`

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# cli great-greets option-replacements

[↩ Parent](#cli-great-greets)

## Usage

```
cli great-greets option-replacements [--app <application>] [--env <environment>] 
                                     [--svc <service>] 
```

## Options

- `--app <text>`

- `--env <text>`

- `--svc <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.
