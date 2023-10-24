# Commands Reference

- [copilot-helper](#copilot-helper)
- [copilot-helper bootstrap](#copilot-helper-bootstrap)
- [copilot-helper bootstrap make-config](#copilot-helper-bootstrap-make-config)
- [copilot-helper bootstrap migrate-secrets](#copilot-helper-bootstrap-migrate-secrets)
- [copilot-helper bootstrap copy-secrets](#copilot-helper-bootstrap-copy-secrets)
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
- [copilot-helper config](#copilot-helper-config)
- [copilot-helper config validate](#copilot-helper-config-validate)
- [copilot-helper copilot](#copilot-helper-copilot)
- [copilot-helper copilot make-addons](#copilot-helper-copilot-make-addons)
- [copilot-helper copilot get-env-secrets](#copilot-helper-copilot-get-env-secrets)
- [copilot-helper domain](#copilot-helper-domain)
- [copilot-helper domain check-domain](#copilot-helper-domain-check-domain)
- [copilot-helper domain assign-domain](#copilot-helper-domain-assign-domain)
- [copilot-helper svc](#copilot-helper-svc)
- [copilot-helper svc deploy](#copilot-helper-svc-deploy)
- [copilot-helper waf](#copilot-helper-waf)
- [copilot-helper waf attach-waf](#copilot-helper-waf-attach-waf)
- [copilot-helper waf custom-waf](#copilot-helper-waf-custom-waf)

# copilot-helper

## Usage

```
copilot-helper <command> [--version] 
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
- [`config` ↪](#copilot-helper-config)
- [`copilot` ↪](#copilot-helper-copilot)
- [`domain` ↪](#copilot-helper-domain)
- [`svc` ↪](#copilot-helper-svc)
- [`waf` ↪](#copilot-helper-waf)

# copilot-helper bootstrap

[↩ Parent](#copilot-helper)

## Usage

```
copilot-helper bootstrap (make-config|migrate-secrets|copy-secrets) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`copy-secrets` ↪](#copilot-helper-bootstrap-copy-secrets)
- [`make-config` ↪](#copilot-helper-bootstrap-make-config)
- [`migrate-secrets` ↪](#copilot-helper-bootstrap-migrate-secrets)

# copilot-helper bootstrap make-config

[↩ Parent](#copilot-helper-bootstrap)

    Generate Copilot boilerplate code.

## Usage

```
copilot-helper bootstrap make-config [-d <directory>] 
```

## Options

- `-d
--directory <text>` _Defaults to .._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper bootstrap migrate-secrets

[↩ Parent](#copilot-helper-bootstrap)

    Migrate secrets from your GOV.UK PaaS application to DBT PaaS.

    You need to be authenticated via Cloud Foundry CLI and the AWS CLI to use this command.

    If you're using AWS profiles, use the AWS_PROFILE environment variable to indicate the which
    profile to use, e.g.:

    AWS_PROFILE=myaccount copilot-bootstrap.py ...

## Usage

```
copilot-helper bootstrap migrate-secrets --project-profile <project_profile> 
                                         [--env <env>] [--svc <svc>] 
                                         [--overwrite] [--dry-run] 
```

## Options

- `--project-profile <text>`
  - AWS account profile name
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
copilot-helper bootstrap copy-secrets <source_environment> <target_environment> 
                                      --project-profile <project_profile> 
```

## Arguments

- `source_environment <text>`
- `target_environment <text>`

## Options

- `--project-profile <text>`
  - AWS account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper check-cloudformation

[↩ Parent](#copilot-helper)

    Runs the checks passed in the command arguments.

    If no argument is passed, it will run all the checks.

## Usage

```
copilot-helper check-cloudformation lint [-d <directory>] 
```

## Options

- `-d
--directory <text>` _Defaults to copilot._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`lint` ↪](#copilot-helper-check-cloudformation-lint)

# copilot-helper check-cloudformation lint

[↩ Parent](#copilot-helper-check-cloudformation)

    Runs cfn-lint against the generated CloudFormation templates.

## Usage

```
copilot-helper check-cloudformation lint [-d <directory>] 
```

## Options

- `-d
--directory <text>` _Defaults to copilot._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild

[↩ Parent](#copilot-helper)

## Usage

```
copilot-helper codebuild <command> 
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
copilot-helper codebuild link-github --pat <pat> --project-profile <project_profile> 
```

## Options

- `--pat <text>`
  - PAT Token
- `--project-profile <text>`
  - AWS account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild create-codedeploy-role

[↩ Parent](#copilot-helper-codebuild)

    Add AWS Role needed for codedeploy.

## Usage

```
copilot-helper codebuild create-codedeploy-role --project-profile <project_profile> 
                                                [--type (ci|custom)] 
```

## Options

- `--project-profile <text>`
  - AWS account profile name
- `--type <choice>` _Defaults to ci._
  - type of project <ci/custom>
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild codedeploy

[↩ Parent](#copilot-helper-codebuild)

    Builds Code build boilerplate.

## Usage

```
copilot-helper codebuild codedeploy --name <name> --git <git> --branch <branch> 
                                    --buildspec <buildspec> --project-profile <project_profile> 
                                    [--desc <desc>] [--update] [--release] 
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
- `--project-profile <text>`
  - AWS account profile name
- `--release <boolean>` _Defaults to False._
  - Trigger builds on release tags
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild buildproject

[↩ Parent](#copilot-helper-codebuild)

    Builds Code build for ad hoc projects.

## Usage

```
copilot-helper codebuild buildproject --name <name> --git <git> 
                                      --branch <branch> --buildspec <buildspec> 
                                      --project-profile <project_profile> 
                                      [--desc <desc>] [--builderimage <builderimage>] 
                                      [--update] 
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
  - AWS account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild delete-project

[↩ Parent](#copilot-helper-codebuild)

    Delete CodeBuild projects.

## Usage

```
copilot-helper codebuild delete-project --name <name> --project-profile <project_profile> 
```

## Options

- `--name <text>`
  - Name of project
- `--project-profile <text>`
  - AWS account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebuild slackcreds

[↩ Parent](#copilot-helper-codebuild)

    Add Slack credentials into AWS Parameter Store.

## Usage

```
copilot-helper codebuild slackcreds --workspace <workspace> --channel <channel> 
                                    --token <token> --project-profile <project_profile> 
```

## Options

- `--workspace <text>`
  - Slack Workspace id
- `--channel <text>`
  - Slack channel id
- `--token <text>`
  - Slack api token
- `--project-profile <text>`
  - AWS account profile name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper conduit

[↩ Parent](#copilot-helper)

    Create a conduit connection to an addon.

## Usage

```
copilot-helper conduit (opensearch|postgres|redis) 
                       --app <app> --env <env> [--addon-name <addon_name>] 
```

## Arguments

- `addon_type <choice>`

## Options

- `--app <text>`
  - AWS application name
- `--env <text>`
  - AWS environment name
- `--addon-name <text>`
  - Name of custom addon
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper config

[↩ Parent](#copilot-helper)

    Perform actions on configuration files.

## Usage

```
copilot-helper config validate 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`validate` ↪](#copilot-helper-config-validate)

# copilot-helper config validate

[↩ Parent](#copilot-helper-config)

    Validate deployment or application configuration.

## Usage

```
copilot-helper config validate 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper copilot

[↩ Parent](#copilot-helper)

## Usage

```
copilot-helper copilot (make-addons|get-env-secrets) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`get-env-secrets` ↪](#copilot-helper-copilot-get-env-secrets)
- [`make-addons` ↪](#copilot-helper-copilot-make-addons)

# copilot-helper copilot make-addons

[↩ Parent](#copilot-helper-copilot)

    Generate addons CloudFormation for each environment.

## Usage

```
copilot-helper copilot make-addons [-d <directory>] 
```

## Options

- `-d
--directory <text>` _Defaults to .._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper copilot get-env-secrets

[↩ Parent](#copilot-helper-copilot)

    List secret names and values for an environment.

## Usage

```
copilot-helper copilot get-env-secrets <app> <env> 
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
copilot-helper domain (check-domain|assign-domain) 
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
copilot-helper domain check-domain --domain-profile (dev|live) --project-profile <project_profile> 
                                   --base-domain <base_domain> [--env <env>] 
```

## Options

- `--domain-profile <choice>`
  - AWS account profile name for Route53 domains account
- `--project-profile <text>`
  - AWS account profile name for certificates account
- `--base-domain <text>`
  - root domain
- `--env <text>`
  - AWS Copilot environment name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper domain assign-domain

[↩ Parent](#copilot-helper-domain)

    Check Route53 domain is pointing to the correct ECS Load Balancer.

## Usage

```
copilot-helper domain assign-domain --app <app> --env <env> --svc <svc> 
                                    --domain-profile (dev|live) 
                                    --project-profile <project_profile> 
```

## Options

- `--app <text>`
  - Application Name
- `--env <text>`
  - Environment
- `--svc <text>`
  - Service Name
- `--domain-profile <choice>`
  - AWS account profile name for Route53 domains account
- `--project-profile <text>`
  - AWS account profile name for application account
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper svc

[↩ Parent](#copilot-helper)

    AWS Copilot svc actions with DBT extras.

## Usage

```
copilot-helper svc deploy 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`deploy` ↪](#copilot-helper-svc-deploy)

# copilot-helper svc deploy

[↩ Parent](#copilot-helper-svc)

    Deploy image tag to a service, defaults to image tagged latest.

## Usage

```
copilot-helper svc deploy --env <env> --name <name> --repository <repository> 
                          [--image-tag <image_tag>] 
```

## Options

- `--env <text>`

- `--name <text>`

- `--repository <text>`

- `--image-tag <text>` _Defaults to latest._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper waf

[↩ Parent](#copilot-helper)

## Usage

```
copilot-helper waf (attach-waf|custom-waf) 
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
copilot-helper waf attach-waf --app <app> --env <env> --svc <svc> 
                              --project-profile <project_profile> 
```

## Options

- `--app <text>`
  - Application Name
- `--env <text>`
  - Environment
- `--svc <text>`
  - Service Name
- `--project-profile <text>`
  - AWS account profile name for application account
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper waf custom-waf

[↩ Parent](#copilot-helper-waf)

    Attach custom WAF to ECS Load Balancer.

## Usage

```
copilot-helper waf custom-waf --app <app> --env <env> --svc <svc> 
                              --project-profile <project_profile> 
                              --waf-path <waf_path> 
```

## Options

- `--app <text>`
  - Application Name
- `--env <text>`
  - Environment
- `--svc <text>`
  - Service Name
- `--project-profile <text>`
  - AWS account profile name for application account
- `--waf-path <text>`
  - path to waf.yml file
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.
