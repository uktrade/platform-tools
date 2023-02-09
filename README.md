# Copilot tools

This repo contains a set of tools for transferring applications from GOV paas to copilot and boostrapping environments.


## Installation

Clone the repo and install the requirements.txt file in a virtualenv.

## copilot-bootstrap.py

This script takes a yaml project config file and outputs the copilot config files along with a set of instructions for boottsrapping the application.

Project config yaml:
```
app: application-name
domain: the-base-domain.uktrade.digital
environments:
  prod:
    certificate_arns:
    - ACM-ARN-FOR-the-production-url.gov.uk
  staging: {}
  dev: {}
services:
- name: api
  image_location: nginx:latest
  repo: git@github.com:uktrade/the-api-repo
  environments:
    dev:
      ipfilter: true
      paas: dit-staging/the-space/app_dev
      url: dev.api.example.uktrade.digital
    staging:
      ipfilter: true
      paas: dit-staging/the-space/app_staging
      url: staging.api.example.uktrade.digital
    staging:
    prod:
      ipfilter: false
      paas: dit-services/the-space/app
      url: the-production-url.gov.uk
  backing-services: "TBD."
```

Run:

`python copilot-bootstrap.py yaml-file-path.yaml ./path/to/root/of/project/repo`

All config files will be generated and a set of instructions for bootstrapping the app will be displayed.


## code-deploy-bootstrap.py

This script is used to bootstrap codebuild configuration in AWS.

There are 3 options to this script.

  * link-github - Pass in a Github PAT to allow CodeDeploy to connect to Github.
  * create-codedeploy-role - Creates a role needed in each AWS account for CodeDeploy to push to ECR.
  * codedeploy - Creates the CodeDeploy project.

Run:

`python code-deploy-bootstrap.py link-github --pat {PAT TOKEN}`
`python code-deploy-bootstrap.py create-codedeploy-role`
`python code-deploy-bootstrap.py codedeploy {--update} --name {service name} --desc {some description} --git {git url} --branch {branch} --buildspec {path/to/buildspec.yml}`
