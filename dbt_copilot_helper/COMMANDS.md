# Commands Reference

- [copilot-helper](#copilot-helper)
- [copilot-helper bootstrap](#copilot-helper-bootstrap)
- [copilot-helper bootstrap make-config](#copilot-helper-bootstrap-make-config)
- [copilot-helper bootstrap migrate-secrets](#copilot-helper-bootstrap-migrate-secrets)
- [copilot-helper bootstrap copy-secrets](#copilot-helper-bootstrap-copy-secrets)
- [copilot-helper check-cloudformation](#copilot-helper-check-cloudformation)
- [copilot-helper check-cloudformation lint](#copilot-helper-check-cloudformation-lint)
- [copilot-helper check-cloudformation check-security](#copilot-helper-check-cloudformation-check-security)
- [copilot-helper codebase](#copilot-helper-codebase)
- [copilot-helper codebase prepare](#copilot-helper-codebase-prepare)
- [copilot-helper codebase list](#copilot-helper-codebase-list)
- [copilot-helper codebase build](#copilot-helper-codebase-build)
- [copilot-helper codebase deploy](#copilot-helper-codebase-deploy)
- [copilot-helper conduit](#copilot-helper-conduit)
- [copilot-helper config](#copilot-helper-config)
- [copilot-helper config validate](#copilot-helper-config-validate)
- [copilot-helper copilot](#copilot-helper-copilot)
- [copilot-helper copilot make-addons](#copilot-helper-copilot-make-addons)
- [copilot-helper copilot get-env-secrets](#copilot-helper-copilot-get-env-secrets)
- [copilot-helper domain](#copilot-helper-domain)
- [copilot-helper domain configure](#copilot-helper-domain-configure)
- [copilot-helper domain assign](#copilot-helper-domain-assign)
- [copilot-helper cdn](#copilot-helper-cdn)
- [copilot-helper cdn assign](#copilot-helper-cdn-assign)
- [copilot-helper cdn delete](#copilot-helper-cdn-delete)
- [copilot-helper cdn list](#copilot-helper-cdn-list)
- [copilot-helper environment](#copilot-helper-environment)
- [copilot-helper environment offline](#copilot-helper-environment-offline)
- [copilot-helper environment online](#copilot-helper-environment-online)
- [copilot-helper pipeline](#copilot-helper-pipeline)
- [copilot-helper pipeline generate](#copilot-helper-pipeline-generate)
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
- [`cdn` ↪](#copilot-helper-cdn)
- [`check-cloudformation` ↪](#copilot-helper-check-cloudformation)
- [`codebase` ↪](#copilot-helper-codebase)
- [`conduit` ↪](#copilot-helper-conduit)
- [`config` ↪](#copilot-helper-config)
- [`copilot` ↪](#copilot-helper-copilot)
- [`domain` ↪](#copilot-helper-domain)
- [`environment` ↪](#copilot-helper-environment)
- [`pipeline` ↪](#copilot-helper-pipeline)
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
                                         --env <env> [--svc <svc>] 
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
copilot-helper check-cloudformation (lint|check-security) 
                                    [-d <directory>] 
```

## Options

- `-d
--directory <text>` _Defaults to copilot._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`check-security` ↪](#copilot-helper-check-cloudformation-check-security)
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

# copilot-helper check-cloudformation check-security

[↩ Parent](#copilot-helper-check-cloudformation)

## Usage

```
copilot-helper check-cloudformation check-security [-d <directory>] 
```

## Options

- `-d
--directory <text>` _Defaults to copilot._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebase

[↩ Parent](#copilot-helper)

    Codebase commands.

## Usage

```
copilot-helper codebase (prepare|list|build|deploy) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`build` ↪](#copilot-helper-codebase-build)
- [`deploy` ↪](#copilot-helper-codebase-deploy)
- [`list` ↪](#copilot-helper-codebase-list)
- [`prepare` ↪](#copilot-helper-codebase-prepare)

# copilot-helper codebase prepare

[↩ Parent](#copilot-helper-codebase)

    Sets up an application codebase for use within a DBT platform project.

## Usage

```
copilot-helper codebase prepare 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebase list

[↩ Parent](#copilot-helper-codebase)

    List available codebases for the application.

## Usage

```
copilot-helper codebase list --app <app> [--with-images] 
```

## Options

- `--app <text>`
  - AWS application name
- `--with-images <boolean>` _Defaults to False._
  - List up to the last 10 images tagged for this codebase
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebase build

[↩ Parent](#copilot-helper-codebase)

    Trigger a CodePipeline pipeline based build.

## Usage

```
copilot-helper codebase build --app <app> --codebase <codebase> 
                              --commit <commit> 
```

## Options

- `--app <text>`
  - AWS application name
- `--codebase <text>`
  - GitHub codebase name
- `--commit <text>`
  - GitHub commit hash
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper codebase deploy

[↩ Parent](#copilot-helper-codebase)

    Trigger a CodePipeline pipeline based deployment.

## Usage

```
copilot-helper codebase deploy --app <app> --env <env> --codebase <codebase> 
                               --commit <commit> 
```

## Options

- `--app <text>`
  - AWS application name
- `--env <text>`
  - AWS Copilot environment
- `--codebase <text>`
  - Codebase name in pipelines.yml file
- `--commit <text>`
  - GitHub commit hash
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper conduit

[↩ Parent](#copilot-helper)

    Create a conduit connection to an addon.

## Usage

```
copilot-helper conduit <addon_name> 
                       --app <app> --env <env> 
```

## Arguments

- `addon_name <text>`

## Options

- `--app <text>`
  - AWS application name
- `--env <text>`
  - AWS environment name
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
copilot-helper domain (configure|assign) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`assign` ↪](#copilot-helper-domain-assign)
- [`configure` ↪](#copilot-helper-domain-configure)

# copilot-helper domain configure

[↩ Parent](#copilot-helper-domain)

    Creates subdomains if they do not exist and then creates certificates for
    them.

## Usage

```
copilot-helper domain configure --project-profile <project_profile> 
                                --env <env> 
```

## Options

- `--project-profile <text>`
  - AWS account profile name for certificates account
- `--env <text>`
  - AWS Copilot environment name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper domain assign

[↩ Parent](#copilot-helper-domain)

    Assigns the load balancer for a service to its domain name.

## Usage

```
copilot-helper domain assign --app <app> --env <env> --svc <svc> 
                             --domain-profile (dev|live) --project-profile <project_profile> 
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

# copilot-helper cdn

[↩ Parent](#copilot-helper)

## Usage

```
copilot-helper cdn (assign|delete|list) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`assign` ↪](#copilot-helper-cdn-assign)
- [`delete` ↪](#copilot-helper-cdn-delete)
- [`list` ↪](#copilot-helper-cdn-list)

# copilot-helper cdn assign

[↩ Parent](#copilot-helper-cdn)

    Assigns a CDN domain name to application loadbalancer.

## Usage

```
copilot-helper cdn assign --project-profile <project_profile> --env <env> 
                          --app <app> --svc <svc> 
```

## Options

- `--project-profile <text>`
  - AWS account profile name for certificates account
- `--env <text>`
  - AWS Copilot environment name
- `--app <text>`
  - Application Name
- `--svc <text>`
  - Service Name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper cdn delete

[↩ Parent](#copilot-helper-cdn)

    Assigns a CDN domain name to application loadbalancer.

## Usage

```
copilot-helper cdn delete --project-profile <project_profile> --env <env> 
                          --app <app> --svc <svc> 
```

## Options

- `--project-profile <text>`
  - AWS account profile name for certificates account
- `--env <text>`
  - AWS Copilot environment name
- `--app <text>`
  - Application Name
- `--svc <text>`
  - Service Name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper cdn list

[↩ Parent](#copilot-helper-cdn)

    List CDN domain name attached to application loadbalancer.

## Usage

```
copilot-helper cdn list --project-profile <project_profile> --env <env> 
                        --app <app> --svc <svc> 
```

## Options

- `--project-profile <text>`
  - AWS account profile name for certificates account
- `--env <text>`
  - AWS Copilot environment name
- `--app <text>`
  - Application Name
- `--svc <text>`
  - Service Name
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper environment

[↩ Parent](#copilot-helper)

    Commands affecting environments.

## Usage

```
copilot-helper environment (offline|online) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`offline` ↪](#copilot-helper-environment-offline)
- [`online` ↪](#copilot-helper-environment-online)

# copilot-helper environment offline

[↩ Parent](#copilot-helper-environment)

    Take load-balanced web services offline with a maintenance page.

## Usage

```
copilot-helper environment offline --app <app> --env <env> [--template (default|migration)] 
```

## Options

- `--app <text>`

- `--env <text>`

- `--template <choice>` _Defaults to default._
  - The maintenance page you wish to put up.
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper environment online

[↩ Parent](#copilot-helper-environment)

    Remove a maintenance page from an environment.

## Usage

```
copilot-helper environment online --app <app> --env <env> 
```

## Options

- `--app <text>`

- `--env <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# copilot-helper pipeline

[↩ Parent](#copilot-helper)

    Pipeline commands.

## Usage

```
copilot-helper pipeline generate 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`generate` ↪](#copilot-helper-pipeline-generate)

# copilot-helper pipeline generate

[↩ Parent](#copilot-helper-pipeline)

    Given a pipelines.yml file, generate environment and service deployment
    pipelines.

## Usage

```
copilot-helper pipeline generate 
```

## Options

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
