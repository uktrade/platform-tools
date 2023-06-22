# Commands

- [copilot-helper](#copilot-helper)
- [copilot-helper bootstrap](#copilot-helper-bootstrap)
- [copilot-helper bootstrap make-config](#copilot-helper-bootstrap-make-config)
- [copilot-helper bootstrap migrate-secrets](#copilot-helper-bootstrap-migrate-secrets)
- [copilot-helper bootstrap instructions](#copilot-helper-bootstrap-instructions)
- [copilot-helper check-cloudformation](#copilot-helper-check-cloudformation)
- [copilot-helper check-cloudformation lint](#copilot-helper-check-cloudformation-lint)
- [copilot-helper copilot](#copilot-helper-copilot)
- [copilot-helper copilot make-storage](#copilot-helper-copilot-make-storage)
- [copilot-helper copilot apply-waf](#copilot-helper-copilot-apply-waf)
- [copilot-helper copilot get-env-secrets](#copilot-helper-copilot-get-env-secrets)
- [copilot-helper codebuild](#copilot-helper-codebuild)
- [copilot-helper codebuild link-github](#copilot-helper-codebuild-link-github)
- [copilot-helper codebuild create-codedeploy-role](#copilot-helper-codebuild-create-codedeploy-role)
- [copilot-helper codebuild codedeploy](#copilot-helper-codebuild-codedeploy)
- [copilot-helper codebuild buildproject](#copilot-helper-codebuild-buildproject)
- [copilot-helper codebuild delete-project](#copilot-helper-codebuild-delete-project)
- [copilot-helper codebuild slackcreds](#copilot-helper-codebuild-slackcreds)
- [copilot-helper domain](#copilot-helper-domain)
- [copilot-helper domain check-domain](#copilot-helper-domain-check-domain)
- [copilot-helper domain assign-domain](#copilot-helper-domain-assign-domain)

# copilot-helper

Base command.

No description.

## Usage

```
Usage: copilot-helper [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--version <boolean>` _Defaults to False._
  -  Show the version and exit.
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

## Commands

- [`bootstrap` ↪](#copilot-helper-bootstrap)
- [`check-cloudformation` ↪](#copilot-helper-check-cloudformation)
- [`codebuild` ↪](#copilot-helper-codebuild)
- [`copilot` ↪](#copilot-helper-copilot)
- [`domain` ↪](#copilot-helper-domain)

## CLI Help

```
Usage: copilot-helper [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  bootstrap
  check-cloudformation  Runs the checks...
  codebuild
  copilot
  domain
```

# copilot-helper bootstrap

[↩ Parent](#copilot-helper)

No description.

## Usage

```
Usage: copilot-helper bootstrap 
           [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

## Commands

- [`instructions` ↪](#copilot-helper-bootstrap-instructions)
- [`make-config` ↪](#copilot-helper-bootstrap-make-config)
- [`migrate-secrets` ↪](#copilot-helper-bootstrap-migrate-secrets)

## CLI Help

```
Usage: copilot-helper bootstrap 
           [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  instructions     Show migration instructions.
  make-config      Generate copilot...
  migrate-secrets  Migrate secrets from your...
```

# copilot-helper bootstrap make-config

[↩ Parent](#copilot-helper-bootstrap)


    Generate copilot boilerplate code.

    CONFIG-FILE is the path to the input yaml config file OUTPUT is the location
    of the repo root dir. Defaults to the current directory.
    

## Usage

```
Usage: copilot-helper bootstrap make-config 
           [OPTIONS] CONFIG_FILE [OUTPUT]
```

## Options

- `config-file <path>`
- `output <path>` _Defaults to .._
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper bootstrap make-config 
           [OPTIONS] CONFIG_FILE [OUTPUT]

  Generate copilot boilerplate code.

  CONFIG-FILE is the path to the input yaml config
  file OUTPUT is the location of the repo root
  dir. Defaults to the current directory.

Options:
  --help  Show this message and exit.
```

# copilot-helper bootstrap migrate-secrets

[↩ Parent](#copilot-helper-bootstrap)


    Migrate secrets from your gov paas application to AWS/copilot.

    You need to be authenticated via cf cli and the AWS cli to use this commmand.

    If you're using AWS profiles, use the AWS_PROFILE env var to indicate the which profile to use, e.g.:

    AWS_PROFILE=myaccount copilot-bootstrap.py ...
    

## Usage

```
Usage: copilot-helper bootstrap migrate-secrets 
           [OPTIONS] CONFIG_FILE
```

## Options

- `config-file <path>`
- `--env <text>`
  -  Migrate secrets from a specific environment
- `--svc <text>`
  -  Migrate secrets from a specific service
- `--overwrite <boolean>` _Defaults to False._
  -  Overwrite existing secrets?
- `--dry-run <boolean>` _Defaults to False._
  -  dry run
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper bootstrap migrate-secrets 
           [OPTIONS] CONFIG_FILE

  Migrate secrets from your gov paas application
  to AWS/copilot.

  You need to be authenticated via cf cli and the
  AWS cli to use this commmand.

  If you're using AWS profiles, use the
  AWS_PROFILE env var to indicate the which
  profile to use, e.g.:

  AWS_PROFILE=myaccount copilot-bootstrap.py ...

Options:
  --env TEXT   Migrate secrets from a specific
               environment
  --svc TEXT   Migrate secrets from a specific
               service
  --overwrite  Overwrite existing secrets?
  --dry-run    dry run
  --help       Show this message and exit.
```

# copilot-helper bootstrap instructions

[↩ Parent](#copilot-helper-bootstrap)

Show migration instructions.

## Usage

```
Usage: copilot-helper bootstrap instructions 
           [OPTIONS] CONFIG_FILE
```

## Options

- `config-file <path>`
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper bootstrap instructions 
           [OPTIONS] CONFIG_FILE

  Show migration instructions.

Options:
  --help  Show this message and exit.
```

# copilot-helper check-cloudformation

[↩ Parent](#copilot-helper)


    Runs the checks passed in the command arguments.

    If no argument is passed, it will run all the checks.
    

## Usage

```
Usage: copilot-helper check-cloudformation 
           [OPTIONS] COMMAND1 [ARGS]... [COMMAND2
           [ARGS]...]...
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

## Commands

- [`lint` ↪](#copilot-helper-check-cloudformation-lint)

## CLI Help

```
Usage: copilot-helper check-cloudformation 
           [OPTIONS] COMMAND1 [ARGS]... [COMMAND2
           [ARGS]...]...

  Runs the checks passed in the command arguments.

  If no argument is passed, it will run all the
  checks.

Options:
  --help  Show this message and exit.

Commands:
  lint  Runs cfn-lint against the generated...
```

# copilot-helper check-cloudformation lint

[↩ Parent](#copilot-helper-check-cloudformation)

Runs cfn-lint against the generated CloudFormation templates.

## Usage

```
Usage: copilot-helper check-cloudformation lint 
           [OPTIONS]
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper check-cloudformation lint 
           [OPTIONS]

  Runs cfn-lint against the generated
  CloudFormation templates.

Options:
  --help  Show this message and exit.
```

# copilot-helper copilot

[↩ Parent](#copilot-helper)

No description.

## Usage

```
Usage: copilot-helper copilot [OPTIONS] COMMAND
                              [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

## Commands

- [`apply-waf` ↪](#copilot-helper-copilot-apply-waf)
- [`get-env-secrets` ↪](#copilot-helper-copilot-get-env-secrets)
- [`make-storage` ↪](#copilot-helper-copilot-make-storage)

## CLI Help

```
Usage: copilot-helper copilot [OPTIONS] COMMAND
                              [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  apply-waf        Apply the WAF environment...
  get-env-secrets  List secret names and...
  make-storage     Generate storage...
```

# copilot-helper copilot make-storage

[↩ Parent](#copilot-helper-copilot)

Generate storage cloudformation for each environment.

## Usage

```
Usage: copilot-helper copilot make-storage 
           [OPTIONS] STORAGE_CONFIG_FILE
```

## Options

- `storage-config-file <path>`
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper copilot make-storage 
           [OPTIONS] STORAGE_CONFIG_FILE

  Generate storage cloudformation for each
  environment.

Options:
  --help  Show this message and exit.
```

# copilot-helper copilot apply-waf

[↩ Parent](#copilot-helper-copilot)

Apply the WAF environment addon.

## Usage

```
Usage: copilot-helper copilot apply-waf 
           [OPTIONS]
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper copilot apply-waf 
           [OPTIONS]

  Apply the WAF environment addon.

Options:
  --help  Show this message and exit.
```

# copilot-helper copilot get-env-secrets

[↩ Parent](#copilot-helper-copilot)

List secret names and values for an environment.

## Usage

```
Usage: copilot-helper copilot get-env-secrets 
           [OPTIONS] APP ENV
```

## Options

- `app <text>`
- `env <text>`
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper copilot get-env-secrets 
           [OPTIONS] APP ENV

  List secret names and values for an environment.

Options:
  --help  Show this message and exit.
```

# copilot-helper codebuild

[↩ Parent](#copilot-helper)

No description.

## Usage

```
Usage: copilot-helper codebuild 
           [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

## Commands

- [`buildproject` ↪](#copilot-helper-codebuild-buildproject)
- [`codedeploy` ↪](#copilot-helper-codebuild-codedeploy)
- [`create-codedeploy-role` ↪](#copilot-helper-codebuild-create-codedeploy-role)
- [`delete-project` ↪](#copilot-helper-codebuild-delete-project)
- [`link-github` ↪](#copilot-helper-codebuild-link-github)
- [`slackcreds` ↪](#copilot-helper-codebuild-slackcreds)

## CLI Help

```
Usage: copilot-helper codebuild 
           [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  buildproject            Builds Code build...
  codedeploy              Builds Code build...
  create-codedeploy-role  Add AWS Role needed...
  delete-project          Delete CodeBuild...
  link-github             Links CodeDeploy to...
  slackcreds              Add Slack...
```

# copilot-helper codebuild link-github

[↩ Parent](#copilot-helper-codebuild)

Links CodeDeploy to Github via users PAT.

## Usage

```
Usage: copilot-helper codebuild link-github 
           [OPTIONS]
```

## Options

- `--pat <text>`
  -  PAT Token
- `--project-profile <text>`
  -  aws account profile name
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper codebuild link-github 
           [OPTIONS]

  Links CodeDeploy to Github via users PAT.

Options:
  --pat TEXT              PAT Token  [required]
  --project-profile TEXT  aws account profile name
                          [required]
  --help                  Show this message and
                          exit.
```

# copilot-helper codebuild create-codedeploy-role

[↩ Parent](#copilot-helper-codebuild)

Add AWS Role needed for codedeploy.

## Usage

```
Usage: copilot-helper codebuild create-codedeploy-role 
           [OPTIONS]
```

## Options

- `--project-profile <text>`
  -  aws account profile name
- `--type <choice>` _Defaults to ci._
  -  type of project <ci/custom>
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper codebuild create-codedeploy-role 
           [OPTIONS]

  Add AWS Role needed for codedeploy.

Options:
  --project-profile TEXT  aws account profile name
                          [required]
  --type [ci|custom]      type of project
                          <ci/custom>
  --help                  Show this message and
                          exit.
```

# copilot-helper codebuild codedeploy

[↩ Parent](#copilot-helper-codebuild)

Builds Code build boilerplate.

## Usage

```
Usage: copilot-helper codebuild codedeploy 
           [OPTIONS]
```

## Options

- `--update <boolean>` _Defaults to False._
  -  Update config
- `--name <text>`
  -  Name of project
- `--desc <text>` _Defaults to ._
  -  Description of project
- `--git <text>`
  -  Git url of code
- `--branch <text>`
  -  Git branch
- `--buildspec <text>`
  -  Location of buildspec file in repo
- `--builderimage <text>` _Defaults to public.ecr.aws/uktrade/ci-image-builder._
  -  Builder image
- `--project-profile <text>`
  -  aws account profile name
- `--release <boolean>` _Defaults to False._
  -  Trigger builds on release tags
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper codebuild codedeploy 
           [OPTIONS]

  Builds Code build boilerplate.

Options:
  --update                Update config
  --name TEXT             Name of project
                          [required]
  --desc TEXT             Description of project
  --git TEXT              Git url of code
                          [required]
  --branch TEXT           Git branch  [required]
  --buildspec TEXT        Location of buildspec
                          file in repo  [required]
  --builderimage TEXT     Builder image
  --project-profile TEXT  aws account profile name
                          [required]
  --release               Trigger builds on
                          release tags
  --help                  Show this message and
                          exit.
```

# copilot-helper codebuild buildproject

[↩ Parent](#copilot-helper-codebuild)

Builds Code build for ad hoc projects.

## Usage

```
Usage: copilot-helper codebuild buildproject 
           [OPTIONS]
```

## Options

- `--update <boolean>` _Defaults to False._
  -  Update config
- `--name <text>`
  -  Name of project
- `--desc <text>` _Defaults to ._
  -  Description of project
- `--git <text>`
  -  Git url of code
- `--branch <text>`
  -  Git branch
- `--buildspec <text>`
  -  Location of buildspec file in repo
- `--builderimage <text>` _Defaults to aws/codebuild/amazonlinux2-x86_64-standard:3.0._
  -  Builder image
- `--project-profile <text>`
  -  aws account profile name
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper codebuild buildproject 
           [OPTIONS]

  Builds Code build for ad hoc projects.

Options:
  --update                Update config
  --name TEXT             Name of project
                          [required]
  --desc TEXT             Description of project
  --git TEXT              Git url of code
                          [required]
  --branch TEXT           Git branch  [required]
  --buildspec TEXT        Location of buildspec
                          file in repo  [required]
  --builderimage TEXT     Builder image
  --project-profile TEXT  aws account profile name
                          [required]
  --help                  Show this message and
                          exit.
```

# copilot-helper codebuild delete-project

[↩ Parent](#copilot-helper-codebuild)

Delete CodeBuild projects.

## Usage

```
Usage: copilot-helper codebuild delete-project 
           [OPTIONS]
```

## Options

- `--name <text>`
  -  Name of project
- `--project-profile <text>`
  -  aws account profile name
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper codebuild delete-project 
           [OPTIONS]

  Delete CodeBuild projects.

Options:
  --name TEXT             Name of project
                          [required]
  --project-profile TEXT  aws account profile name
                          [required]
  --help                  Show this message and
                          exit.
```

# copilot-helper codebuild slackcreds

[↩ Parent](#copilot-helper-codebuild)

Add Slack credentials into AWS Parameter Store.

## Usage

```
Usage: copilot-helper codebuild slackcreds 
           [OPTIONS]
```

## Options

- `--workspace <text>`
  -  Slack Workspace id
- `--channel <text>`
  -  Slack channel id
- `--token <text>`
  -  Slack api token
- `--project-profile <text>`
  -  aws account profile name
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper codebuild slackcreds 
           [OPTIONS]

  Add Slack credentials into AWS Parameter Store.

Options:
  --workspace TEXT        Slack Workspace id
                          [required]
  --channel TEXT          Slack channel id
                          [required]
  --token TEXT            Slack api token
                          [required]
  --project-profile TEXT  aws account profile name
                          [required]
  --help                  Show this message and
                          exit.
```

# copilot-helper domain

[↩ Parent](#copilot-helper)

No description.

## Usage

```
Usage: copilot-helper domain [OPTIONS] COMMAND
                             [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

## Commands

- [`assign-domain` ↪](#copilot-helper-domain-assign-domain)
- [`check-domain` ↪](#copilot-helper-domain-check-domain)

## CLI Help

```
Usage: copilot-helper domain [OPTIONS] COMMAND
                             [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  assign-domain  Check R53 domain is pointing...
  check-domain   Scans to see if Domain exists.
```

# copilot-helper domain check-domain

[↩ Parent](#copilot-helper-domain)

Scans to see if Domain exists.

## Usage

```
Usage: copilot-helper domain check-domain 
           [OPTIONS]
```

## Options

- `--path <text>`
  -  path of copilot folder
- `--domain-profile <text>`
  -  aws account profile name for R53 domains account
- `--project-profile <text>`
  -  aws account profile name for certificates account
- `--base-domain <text>`
  -  root domain
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper domain check-domain 
           [OPTIONS]

  Scans to see if Domain exists.

Options:
  --path TEXT             path of copilot folder
                          [required]
  --domain-profile TEXT   aws account profile name
                          for R53 domains account
                          [required]
  --project-profile TEXT  aws account profile name
                          for certificates account
                          [required]
  --base-domain TEXT      root domain  [required]
  --help                  Show this message and
                          exit.
```

# copilot-helper domain assign-domain

[↩ Parent](#copilot-helper-domain)

Check R53 domain is pointing to the correct ECS Load Blanacer.

## Usage

```
Usage: copilot-helper domain assign-domain 
           [OPTIONS]
```

## Options

- `--app <text>`
  -  Application Name
- `--domain-profile <text>`
  -  aws account profile name for R53 domains account
- `--project-profile <text>`
  -  aws account profile name for application account
- `--svc <text>`
  -  Service Name
- `--env <text>`
  -  Environment
- `--help <boolean>` _Defaults to False._
  -  Show this message and exit.

No commands.

## CLI Help

```
Usage: copilot-helper domain assign-domain 
           [OPTIONS]

  Check R53 domain is pointing to the correct ECS
  Load Blanacer.

Options:
  --app TEXT              Application Name
                          [required]
  --domain-profile TEXT   aws account profile name
                          for R53 domains account
                          [required]
  --project-profile TEXT  aws account profile name
                          for application account
                          [required]
  --svc TEXT              Service Name  [required]
  --env TEXT              Environment  [required]
  --help                  Show this message and
                          exit.
```
