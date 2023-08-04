# Commands Reference

- [copilot-helper](#copilot-helper)
- [copilot-helper bootstrap](#copilot-helper-bootstrap)
- [copilot-helper bootstrap make-config](#copilot-helper-bootstrap-make-config)
- [copilot-helper bootstrap migrate-secrets](#copilot-helper-bootstrap-migrate-secrets)
- [copilot-helper bootstrap copy-secrets](#copilot-helper-bootstrap-copy-secrets)
- [copilot-helper bootstrap instructions](#copilot-helper-bootstrap-instructions)
- [copilot-helper check-cloudformation](#copilot-helper-check-cloudformation)
- [copilot-helper check-cloudformation lint](#copilot-helper-check-cloudformation-lint)
- [copilot-helper codebuild](#copilot-helper-codebuild)
- [copilot-helper codebuild link-github](#copilot-helper-codebuild-link-github)
- [copilot-helper codebuild create-codedeploy-role](#copilot-helper-codebuild-create-codedeploy-role)
- [copilot-helper codebuild codedeploy](#copilot-helper-codebuild-codedeploy)
- [copilot-helper codebuild buildproject](#copilot-helper-codebuild-buildproject)
- [copilot-helper codebuild delete-project](#copilot-helper-codebuild-delete-project)
- [copilot-helper codebuild slackcreds](#copilot-helper-codebuild-slackcreds)
- [copilot-helper conduit](#copilot-helper-conduit)
- [copilot-helper conduit tunnel](#copilot-helper-conduit-tunnel)
- [copilot-helper copilot](#copilot-helper-copilot)
- [copilot-helper copilot make-storage](#copilot-helper-copilot-make-storage)
- [copilot-helper copilot get-env-secrets](#copilot-helper-copilot-get-env-secrets)
- [copilot-helper domain](#copilot-helper-domain)
- [copilot-helper domain check-domain](#copilot-helper-domain-check-domain)
- [copilot-helper domain assign-domain](#copilot-helper-domain-assign-domain)
- [copilot-helper waf](#copilot-helper-waf)
- [copilot-helper waf attach-waf](#copilot-helper-waf-attach-waf)
- [copilot-helper waf custom-waf](#copilot-helper-waf-custom-waf)

# copilot-helper

## Usage

```
Usage: copilot-helper [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--version <boolean>` _Defaults to False._
  - Show the version and exit.
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`bootstrap` ↪](#copilot-helper-bootstrap)
- [`check-cloudformation` ↪](#copilot-helper-check-cloudformation)
- [`codebuild` ↪](#copilot-helper-codebuild)
- [`conduit` ↪](#copilot-helper-conduit)
- [`copilot` ↪](#copilot-helper-copilot)
- [`domain` ↪](#copilot-helper-domain)
- [`waf` ↪](#copilot-helper-waf)

# copilot-helper bootstrap

[↩ Parent](#copilot-helper)

## Usage

```
Usage: copilot-helper bootstrap [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`copy-secrets` ↪](#copilot-helper-bootstrap-copy-secrets)
- [`instructions` ↪](#copilot-helper-bootstrap-instructions)
- [`make-config` ↪](#copilot-helper-bootstrap-make-config)
- [`migrate-secrets` ↪](#copilot-helper-bootstrap-migrate-secrets)

# copilot-helper bootstrap make-config

[↩ Parent](#copilot-helper-bootstrap)

    Generate Copilot boilerplate code.

## Usage

```
Usage: copilot-helper bootstrap make-config [OPTIONS]
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper bootstrap migrate-secrets

[↩ Parent](#copilot-helper-bootstrap)

    Migrate secrets from your gov paas application to AWS/copilot.

    You need to be authenticated via cf cli and the AWS cli to use this commmand.

    If you're using AWS profiles, use the AWS_PROFILE env var to indicate the which profile to use, e.g.:

    AWS_PROFILE=myaccount copilot-bootstrap.py ...

## Usage

```
Usage: copilot-helper bootstrap migrate-secrets [OPTIONS]
```

## Options

- `--project-profile <text>`
  - aws account profile name
- `--env <text>`
  - Migrate secrets from a specific environment
- `--svc <text>`
  - Migrate secrets from a specific service
- `--overwrite <boolean>` _Defaults to False._
  - Overwrite existing secrets?
- `--dry-run <boolean>` _Defaults to False._
  - dry run
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper bootstrap copy-secrets

[↩ Parent](#copilot-helper-bootstrap)

    Copy secrets from one environment to a new environment.

## Usage

```
Usage: copilot-helper bootstrap copy-secrets [OPTIONS] SOURCE_ENVIRONMENT
                                             TARGET_ENVIRONMENT
```

## Arguments

- `source_environment <text>`
- `target_environment <text>`

## Options

- `--project-profile <text>`
  - AWS account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper bootstrap instructions

[↩ Parent](#copilot-helper-bootstrap)

    Show migration instructions.

## Usage

```
Usage: copilot-helper bootstrap instructions [OPTIONS]
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper check-cloudformation

[↩ Parent](#copilot-helper)

    Runs the checks passed in the command arguments.

    If no argument is passed, it will run all the checks.

## Usage

```
Usage: copilot-helper check-cloudformation [OPTIONS] COMMAND1 [ARGS]...
                                           [COMMAND2 [ARGS]...]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`lint` ↪](#copilot-helper-check-cloudformation-lint)

# copilot-helper check-cloudformation lint

[↩ Parent](#copilot-helper-check-cloudformation)

    Runs cfn-lint against the generated CloudFormation templates.

## Usage

```
Usage: copilot-helper check-cloudformation lint [OPTIONS]
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild

[↩ Parent](#copilot-helper)

## Usage

```
Usage: copilot-helper codebuild [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`buildproject` ↪](#copilot-helper-codebuild-buildproject)
- [`codedeploy` ↪](#copilot-helper-codebuild-codedeploy)
- [`create-codedeploy-role` ↪](#copilot-helper-codebuild-create-codedeploy-role)
- [`delete-project` ↪](#copilot-helper-codebuild-delete-project)
- [`link-github` ↪](#copilot-helper-codebuild-link-github)
- [`slackcreds` ↪](#copilot-helper-codebuild-slackcreds)

# copilot-helper codebuild link-github

[↩ Parent](#copilot-helper-codebuild)

    Links CodeDeploy to Github via users PAT.

## Usage

```
Usage: copilot-helper codebuild link-github [OPTIONS]
```

## Options

- `--pat <text>`
  - PAT Token
- `--project-profile <text>`
  - aws account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild create-codedeploy-role

[↩ Parent](#copilot-helper-codebuild)

    Add AWS Role needed for codedeploy.

## Usage

```
Usage: copilot-helper codebuild create-codedeploy-role [OPTIONS]
```

## Options

- `--project-profile <text>`
  - aws account profile name
- `--type <choice>` _Defaults to ci._
  - type of project <ci/custom>
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild codedeploy

[↩ Parent](#copilot-helper-codebuild)

    Builds Code build boilerplate.

## Usage

```
Usage: copilot-helper codebuild codedeploy [OPTIONS]
```

## Options

- `--update <boolean>` _Defaults to False._
  - Update config
- `--name <text>`
  - Name of project
- `--desc <text>` _Defaults to ._
  - Description of project
- `--git <text>`
  - Git url of code
- `--branch <text>`
  - Git branch
- `--buildspec <text>`
  - Location of buildspec file in repo
- `--builderimage <text>` _Defaults to public.ecr.aws/uktrade/ci-image-builder._
  - Builder image
- `--project-profile <text>`
  - aws account profile name
- `--release <boolean>` _Defaults to False._
  - Trigger builds on release tags
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild buildproject

[↩ Parent](#copilot-helper-codebuild)

    Builds Code build for ad hoc projects.

## Usage

```
Usage: copilot-helper codebuild buildproject [OPTIONS]
```

## Options

- `--update <boolean>` _Defaults to False._
  - Update config
- `--name <text>`
  - Name of project
- `--desc <text>` _Defaults to ._
  - Description of project
- `--git <text>`
  - Git url of code
- `--branch <text>`
  - Git branch
- `--buildspec <text>`
  - Location of buildspec file in repo
- `--builderimage <text>` _Defaults to aws/codebuild/amazonlinux2-x86_64-standard:3.0._
  - Builder image
- `--project-profile <text>`
  - aws account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild delete-project

[↩ Parent](#copilot-helper-codebuild)

    Delete CodeBuild projects.

## Usage

```
Usage: copilot-helper codebuild delete-project [OPTIONS]
```

## Options

- `--name <text>`
  - Name of project
- `--project-profile <text>`
  - aws account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild slackcreds

[↩ Parent](#copilot-helper-codebuild)

    Add Slack credentials into AWS Parameter Store.

## Usage

```
Usage: copilot-helper codebuild slackcreds [OPTIONS]
```

## Options

- `--workspace <text>`
  - Slack Workspace id
- `--channel <text>`
  - Slack channel id
- `--token <text>`
  - Slack api token
- `--project-profile <text>`
  - aws account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper conduit

[↩ Parent](#copilot-helper)

## Usage

```
Usage: copilot-helper conduit [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`tunnel` ↪](#copilot-helper-conduit-tunnel)

# copilot-helper conduit tunnel

[↩ Parent](#copilot-helper-conduit)

## Usage

```
Usage: copilot-helper conduit tunnel [OPTIONS]
```

## Options

- `--project-profile <text>`
  - AWS account profile name
- `--app <text>`
  - AWS application name
- `--env <text>`
  - AWS environment name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper copilot

[↩ Parent](#copilot-helper)

## Usage

```
Usage: copilot-helper copilot [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`get-env-secrets` ↪](#copilot-helper-copilot-get-env-secrets)
- [`make-storage` ↪](#copilot-helper-copilot-make-storage)

# copilot-helper copilot make-storage

[↩ Parent](#copilot-helper-copilot)

    Generate storage CloudFormation for each environment.

## Usage

```
Usage: copilot-helper copilot make-storage [OPTIONS]
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper copilot get-env-secrets

[↩ Parent](#copilot-helper-copilot)

    List secret names and values for an environment.

## Usage

```
Usage: copilot-helper copilot get-env-secrets [OPTIONS] APP ENV
```

## Arguments

- `app <text>`
- `env <text>`

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper domain

[↩ Parent](#copilot-helper)

## Usage

```
Usage: copilot-helper domain [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`assign-domain` ↪](#copilot-helper-domain-assign-domain)
- [`check-domain` ↪](#copilot-helper-domain-check-domain)

# copilot-helper domain check-domain

[↩ Parent](#copilot-helper-domain)

    Scans to see if Domain exists.

## Usage

```
Usage: copilot-helper domain check-domain [OPTIONS]
```

## Options

- `--domain-profile <text>`
  - aws account profile name for R53 domains account
- `--project-profile <text>`
  - aws account profile name for certificates account
- `--base-domain <text>`
  - root domain
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper domain assign-domain

[↩ Parent](#copilot-helper-domain)

    Check R53 domain is pointing to the correct ECS Load Blanacer.

## Usage

```
Usage: copilot-helper domain assign-domain [OPTIONS]
```

## Options

- `--app <text>`
  - Application Name
- `--domain-profile <text>`
  - aws account profile name for R53 domains account
- `--project-profile <text>`
  - aws account profile name for application account
- `--svc <text>`
  - Service Name
- `--env <text>`
  - Environment
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper waf

[↩ Parent](#copilot-helper)

## Usage

```
Usage: copilot-helper waf [OPTIONS] COMMAND [ARGS]...
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`attach-waf` ↪](#copilot-helper-waf-attach-waf)
- [`custom-waf` ↪](#copilot-helper-waf-custom-waf)

# copilot-helper waf attach-waf

[↩ Parent](#copilot-helper-waf)

    Attach default WAF rule to ECS Load Balancer.

## Usage

```
Usage: copilot-helper waf attach-waf [OPTIONS]
```

## Options

- `--app <text>`
  - Application Name
- `--project-profile <text>`
  - aws account profile name for application account
- `--svc <text>`
  - Service Name
- `--env <text>`
  - Environment
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper waf custom-waf

[↩ Parent](#copilot-helper-waf)

    Attach custom WAF to ECS Load Balancer.

## Usage

```
Usage: copilot-helper waf custom-waf [OPTIONS]
```

## Options

- `--app <text>`
  - Application Name
- `--project-profile <text>`
  - aws account profile name for application account
- `--svc <text>`
  - Service Name
- `--env <text>`
  - Environment
- `--waf-path <text>`
  - path to waf.yml file
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.
