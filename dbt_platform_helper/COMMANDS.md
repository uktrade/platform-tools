# Commands Reference

- [platform-helper](#platform-helper)
- [platform-helper application](#platform-helper-application)
- [platform-helper application container-stats](#platform-helper-application-container-stats)
- [platform-helper application task-stats](#platform-helper-application-task-stats)
- [platform-helper codebase](#platform-helper-codebase)
- [platform-helper codebase prepare](#platform-helper-codebase-prepare)
- [platform-helper codebase list](#platform-helper-codebase-list)
- [platform-helper codebase build](#platform-helper-codebase-build)
- [platform-helper codebase deploy](#platform-helper-codebase-deploy)
- [platform-helper conduit](#platform-helper-conduit)
- [platform-helper config](#platform-helper-config)
- [platform-helper config validate](#platform-helper-config-validate)
- [platform-helper config aws](#platform-helper-config-aws)
- [platform-helper copilot](#platform-helper-copilot)
- [platform-helper copilot make-addons](#platform-helper-copilot-make-addons)
- [platform-helper environment](#platform-helper-environment)
- [platform-helper environment offline](#platform-helper-environment-offline)
- [platform-helper environment online](#platform-helper-environment-online)
- [platform-helper environment generate](#platform-helper-environment-generate)
- [platform-helper environment generate-terraform](#platform-helper-environment-generate-terraform)
- [platform-helper generate](#platform-helper-generate)
- [platform-helper pipeline](#platform-helper-pipeline)
- [platform-helper pipeline generate](#platform-helper-pipeline-generate)
- [platform-helper secrets](#platform-helper-secrets)
- [platform-helper secrets copy](#platform-helper-secrets-copy)
- [platform-helper secrets list](#platform-helper-secrets-list)
- [platform-helper notify](#platform-helper-notify)
- [platform-helper notify environment-progress](#platform-helper-notify-environment-progress)
- [platform-helper notify add-comment](#platform-helper-notify-add-comment)
- [platform-helper database](#platform-helper-database)
- [platform-helper database dump](#platform-helper-database-dump)
- [platform-helper database load](#platform-helper-database-load)
- [platform-helper database copy](#platform-helper-database-copy)
- [platform-helper version](#platform-helper-version)
- [platform-helper version get-platform-helper-for-project](#platform-helper-version-get-platform-helper-for-project)

# platform-helper

## Usage

```
platform-helper <command> [--version] 
```

## Options

- `--version <boolean>` _Defaults to False._
  - Show the version and exit.
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`application` ↪](#platform-helper-application)
- [`codebase` ↪](#platform-helper-codebase)
- [`conduit` ↪](#platform-helper-conduit)
- [`config` ↪](#platform-helper-config)
- [`copilot` ↪](#platform-helper-copilot)
- [`database` ↪](#platform-helper-database)
- [`environment` ↪](#platform-helper-environment)
- [`generate` ↪](#platform-helper-generate)
- [`notify` ↪](#platform-helper-notify)
- [`pipeline` ↪](#platform-helper-pipeline)
- [`secrets` ↪](#platform-helper-secrets)
- [`version` ↪](#platform-helper-version)

# platform-helper application

[↩ Parent](#platform-helper)

    [DEPRECATED] Application metrics.

## Usage

```
platform-helper application (container-stats|task-stats) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`container-stats` ↪](#platform-helper-application-container-stats)
- [`task-stats` ↪](#platform-helper-application-task-stats)

# platform-helper application container-stats

[↩ Parent](#platform-helper-application)

    [DEPRECATED] Command to get application container level metrics.

## Usage

```
platform-helper application container-stats --env <environment> --app <application> 
                                            [--storage] [--network] 
```

## Options

- `--env <text>`

- `--app <text>`

- `--storage <boolean>` _Defaults to False._

- `--network <boolean>` _Defaults to False._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper application task-stats

[↩ Parent](#platform-helper-application)

    [DEPRECATED] Command to get application task level metrics.

## Usage

```
platform-helper application task-stats --env <environment> --app <application> [--disk] 
                                       [--storage] [--network] 
```

## Options

- `--env <text>`

- `--app <text>`

- `--disk <boolean>` _Defaults to False._

- `--storage <boolean>` _Defaults to False._

- `--network <boolean>` _Defaults to False._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper codebase

[↩ Parent](#platform-helper)

    Codebase commands.

## Usage

```
platform-helper codebase (prepare|list|build|deploy) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`build` ↪](#platform-helper-codebase-build)
- [`deploy` ↪](#platform-helper-codebase-deploy)
- [`list` ↪](#platform-helper-codebase-list)
- [`prepare` ↪](#platform-helper-codebase-prepare)

# platform-helper codebase prepare

[↩ Parent](#platform-helper-codebase)

    Sets up an application codebase for use within a DBT platform project.

## Usage

```
platform-helper codebase prepare 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper codebase list

[↩ Parent](#platform-helper-codebase)

    List available codebases for the application.

## Usage

```
platform-helper codebase list --app <application> [--with-images] 
```

## Options

- `--app <text>`
  - AWS application name
- `--with-images <boolean>` _Defaults to False._
  - List up to the last 10 images tagged for this codebase
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper codebase build

[↩ Parent](#platform-helper-codebase)

    Trigger a CodePipeline pipeline based build.

## Usage

```
platform-helper codebase build --app <application> --codebase <codebase> 
                               --commit <commit> 
```

## Options

- `--app <text>`
  - AWS application name
- `--codebase <text>`
  - The codebase name as specified in the platform-config.yml file
- `--commit <text>`
  - GitHub commit hash
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper codebase deploy

[↩ Parent](#platform-helper-codebase)

## Usage

```
platform-helper codebase deploy --app <application> --env <environment> --codebase <codebase> 
                                --commit <commit> 
```

## Options

- `--app <text>`
  - AWS application name
- `--env <text>`
  - AWS Copilot environment
- `--codebase <text>`
  - The codebase name as specified in the platform-config.yml file
- `--commit <text>`
  - GitHub commit hash
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper conduit

[↩ Parent](#platform-helper)

    Create a conduit connection to an addon.

## Usage

```
platform-helper conduit <addon_name> 
                        --app <application> --env <environment> [--access (read|write|admin)] 
```

## Arguments

- `addon_name <text>`

## Options

- `--app <text>`
  - AWS application name
- `--env <text>`
  - AWS environment name
- `--access <choice>` _Defaults to read._
  - Allow write or admin access to database addons
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper config

[↩ Parent](#platform-helper)

    Perform actions on configuration files.

## Usage

```
platform-helper config (validate|aws) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`aws` ↪](#platform-helper-config-aws)
- [`validate` ↪](#platform-helper-config-validate)

# platform-helper config validate

[↩ Parent](#platform-helper-config)

    Validate deployment or application configuration.

## Usage

```
platform-helper config validate 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper config aws

[↩ Parent](#platform-helper-config)

    Writes a local config file containing all the AWS profiles to which the
    logged in user has access.

    If no `--file-path` is specified, defaults to `~/.aws/config`.

## Usage

```
platform-helper config aws [--file-path <file_path>] 
```

## Options

- `--file-path
-fp <text>` _Defaults to ~/.aws/config._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper copilot

[↩ Parent](#platform-helper)

## Usage

```
platform-helper copilot make-addons 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`make-addons` ↪](#platform-helper-copilot-make-addons)

# platform-helper copilot make-addons

[↩ Parent](#platform-helper-copilot)

    Generate addons CloudFormation for each environment.

## Usage

```
platform-helper copilot make-addons 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper environment

[↩ Parent](#platform-helper)

    Commands affecting environments.

## Usage

```
platform-helper environment (offline|online|generate|generate-terraform) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`generate` ↪](#platform-helper-environment-generate)
- [`generate-terraform` ↪](#platform-helper-environment-generate-terraform)
- [`offline` ↪](#platform-helper-environment-offline)
- [`online` ↪](#platform-helper-environment-online)

# platform-helper environment offline

[↩ Parent](#platform-helper-environment)

    Take load-balanced web services offline with a maintenance page.

## Usage

```
platform-helper environment offline --app <application> --env <environment> --svc <service> 
                                    [--template (default|migration|dmas-migration)] 
                                    [--vpc <vpc>] 
```

## Options

- `--app <text>`

- `--env <text>`

- `--svc <text>` _Defaults to ['web']._

- `--template <choice>` _Defaults to default._
  - The maintenance page you wish to put up.
- `--vpc <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper environment online

[↩ Parent](#platform-helper-environment)

    Remove a maintenance page from an environment.

## Usage

```
platform-helper environment online --app <application> --env <environment> 
```

## Options

- `--app <text>`

- `--env <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper environment generate

[↩ Parent](#platform-helper-environment)

## Usage

```
platform-helper environment generate --name <name> [--vpc-name <vpc_name>] 
```

## Options

- `--vpc-name <text>`

- `--name
-n <text>`

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper environment generate-terraform

[↩ Parent](#platform-helper-environment)

    Generate terraform manifest for the specified environment.

## Usage

```
platform-helper environment generate-terraform --name <name> [--terraform-platform-modules-version <terraform_platform_modules_version>] 
```

## Options

- `--name
-n <text>`
  - The name of the environment to generate a manifest for.
- `--terraform-platform-modules-version <text>`
  - Override the default version of terraform-platform-modules. (Default version is '5').
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper generate

[↩ Parent](#platform-helper)

    Generate deployment pipeline configuration files and generate addons
    CloudFormation template files for each environment.

    Wraps pipeline generate and make-addons.

## Usage

```
platform-helper generate 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper pipeline

[↩ Parent](#platform-helper)

    Pipeline commands.

## Usage

```
platform-helper pipeline generate 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`generate` ↪](#platform-helper-pipeline-generate)

# platform-helper pipeline generate

[↩ Parent](#platform-helper-pipeline)

    Given a platform-config.yml file, generate environment and service
    deployment pipelines.

    This command does the following in relation to the environment pipelines:
    - Reads contents of `platform-config.yml/environment-pipelines` configuration.
      The `terraform/environment-pipelines/<aws_account>/main.tf` file is generated using this configuration.
      The `main.tf` file is then used to generate Terraform for creating an environment pipeline resource.

    This command does the following in relation to the codebase pipelines:
    - Generates the copilot pipeline manifest.yml for copilot/pipelines/<codebase_pipeline_name>

    (Deprecated) This command does the following for non terraform projects (legacy AWS Copilot):
    - Generates the copilot manifest.yml for copilot/environments/<environment>

## Usage

```
platform-helper pipeline generate [--terraform-platform-modules-version <terraform_platform_modules_version>] 
                                  [--deploy-branch <deploy_branch>] 
```

## Options

- `--terraform-platform-modules-version <text>`
  - Override the default version of terraform-platform-modules with a specific version or branch. 
Precedence of version used is version supplied via CLI, then the version found in 
platform-config.yml/default_versions/terraform-platform-modules. 
In absence of these inputs, defaults to version '5'.
- `--deploy-branch <text>`
  - Specify the branch of <application>-deploy used to configure the source stage in the environment-pipeline resource. 
This is generated from the terraform/environments-pipeline/<aws_account>/main.tf file. 
(Default <application>-deploy branch is specified in 
<application>-deploy/platform-config.yml/environment_pipelines/<environment-pipeline>/branch).
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper secrets

[↩ Parent](#platform-helper)

## Usage

```
platform-helper secrets (copy|list) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`copy` ↪](#platform-helper-secrets-copy)
- [`list` ↪](#platform-helper-secrets-list)

# platform-helper secrets copy

[↩ Parent](#platform-helper-secrets)

    Copy secrets from one environment to a new environment.

## Usage

```
platform-helper secrets copy <source_environment> <target_environment> 
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

# platform-helper secrets list

[↩ Parent](#platform-helper-secrets)

    List secret names and values for an environment.

## Usage

```
platform-helper secrets list <application> <environment> 
```

## Arguments

- `app <text>`
- `env <text>`

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper notify

[↩ Parent](#platform-helper)

    Send Slack notifications

## Usage

```
platform-helper notify (environment-progress|add-comment) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`add-comment` ↪](#platform-helper-notify-add-comment)
- [`environment-progress` ↪](#platform-helper-notify-environment-progress)

# platform-helper notify environment-progress

[↩ Parent](#platform-helper-notify)

    Send environment progress notifications

## Usage

```
platform-helper notify environment-progress <slack_channel_id> <slack_token> 
                                            <message> 
                                            [--build-arn <build_arn>] 
                                            [--repository <repository>] 
                                            [--commit-sha <commit_sha>] 
                                            [--slack-ref <slack_ref>] 
```

## Arguments

- `slack-channel-id <text>`
- `slack-token <text>`
- `message <text>`

## Options

- `--build-arn <text>`

- `--repository <text>`

- `--commit-sha <text>`

- `--slack-ref <text>`
  - Slack message reference
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper notify add-comment

[↩ Parent](#platform-helper-notify)

    Add comment to a notification

## Usage

```
platform-helper notify add-comment <slack_channel_id> <slack_token> 
                                   <slack_ref> <message> 
                                   [--title <title>] [--send-to-main-channel <send_to_main_channel>] 
```

## Arguments

- `slack-channel-id <text>`
- `slack-token <text>`
- `slack-ref <text>`
- `message <text>`

## Options

- `--title <text>`
  - Message title
- `--send-to-main-channel <boolean>` _Defaults to False._
  - Send to main channel
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper database

[↩ Parent](#platform-helper)

    Commands to copy data between databases.

## Usage

```
platform-helper database (dump|load|copy) 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`copy` ↪](#platform-helper-database-copy)
- [`dump` ↪](#platform-helper-database-dump)
- [`load` ↪](#platform-helper-database-load)

# platform-helper database dump

[↩ Parent](#platform-helper-database)

    Dump a database into an S3 bucket.

## Usage

```
platform-helper database dump --from <from_env> --database <database> 
                              [--app <application>] [--from-vpc <from_vpc>] 
```

## Options

- `--app <text>`
  - The application name. Required unless you are running the command from your deploy repo
- `--from <text>`
  - The environment you are dumping data from
- `--database <text>`
  - The name of the database you are dumping data from
- `--from-vpc <text>`
  - The vpc the specified environment is running in. Required unless you are running the command from your deploy repo
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper database load

[↩ Parent](#platform-helper-database)

    Load a database from an S3 bucket.

## Usage

```
platform-helper database load --to <to_env> --database <database> 
                              [--app <application>] [--to-vpc <to_vpc>] 
                              [--auto-approve] 
```

## Options

- `--app <text>`
  - The application name. Required unless you are running the command from your deploy repo
- `--to <text>`
  - The environment you are loading data into
- `--database <text>`
  - The name of the database you are loading data into
- `--to-vpc <text>`
  - The vpc the specified environment is running in. Required unless you are running the command from your deploy repo
- `--auto-approve <boolean>` _Defaults to False._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper database copy

[↩ Parent](#platform-helper-database)

    Copy a database between environments.

## Usage

```
platform-helper database copy --from <from_env> --to <to_env> --database <database> 
                              --svc <service> [--app <application>] [--from-vpc <from_vpc>] 
                              [--to-vpc <to_vpc>] [--template (default|migration|dmas-migration)] 
                              [--auto-approve] [--no-maintenance-page] 
```

## Options

- `--app <text>`
  - The application name. Required unless you are running the command from your deploy repo
- `--from <text>`
  - The environment you are copying data from
- `--to <text>`
  - The environment you are copying data into
- `--database <text>`
  - The name of the database you are copying
- `--from-vpc <text>`
  - The vpc the environment you are copying from is running in. Required unless you are running the command from your deploy repo
- `--to-vpc <text>`
  - The vpc the environment you are copying into is running in. Required unless you are running the command from your deploy repo
- `--auto-approve <boolean>` _Defaults to False._

- `--svc <text>` _Defaults to ['web']._

- `--template <choice>` _Defaults to default._
  - The maintenance page you wish to put up.
- `--no-maintenance-page <boolean>` _Defaults to False._

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

# platform-helper version

[↩ Parent](#platform-helper)

    Contains subcommands for getting version information about the
        current project.

## Usage

```
platform-helper version get-platform-helper-for-project 
```

## Options

- `--help <boolean>` _Defaults to False._
  - Show this message and exit.

## Commands

- [`get-platform-helper-for-project` ↪](#platform-helper-version-get-platform-helper-for-project)

# platform-helper version get-platform-helper-for-project

[↩ Parent](#platform-helper-version)

    Print the version of platform-tools required by the current project

## Usage

```
platform-helper version get-platform-helper-for-project [--pipeline <pipeline>] 
```

## Options

- `--pipeline <text>`
  - Take into account platform-tools version overrides in the specified pipeline
- `--help <boolean>` _Defaults to False._
  - Show this message and exit.
