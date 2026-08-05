# `copilot-bootstrap` Image

This image is used as a very light placeholder when deploying DBT Platform infrastructure. It allows us to get the infrastructure into a decent position before we start involving application code and all the variables that adds.

The image is published to [uktrade/copilot-bootstrap](https://gallery.ecr.aws/uktrade/copilot-bootstrap) in the ECR public gallery.

As it will almost never change, there is no automated build and publish at present, just these manual steps.

```shell
aws sso login
AWS_PROFILE=platform-tools aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/uktrade
docker build -t public.ecr.aws/uktrade/copilot-bootstrap:latest --platform linux/amd64 .
docker tag public.ecr.aws/uktrade/copilot-bootstrap:latest public.ecr.aws/uktrade/copilot-bootstrap:<current_platform_tools_release_tag>
docker run public.ecr.aws/uktrade/copilot-bootstrap:latest # Quick test locally before publishing
docker push public.ecr.aws/uktrade/copilot-bootstrap:15.34.1
docker push public.ecr.aws/uktrade/copilot-bootstrap:latest
docker logout public.ecr.aws/uktrade
```

## Pingdom

To allow for the standard healthcheck endpoint `/pingdom/ping.xml`, this image uses a static XML file. 

This allows the AWS Copilot configuration for health checks to be set prior to replacing the bootstrap image with an actual application. In addition, pingdom health checks can be created during the environment setup, allowing the migration team to be alerted should the to-be production environment experience issues.
