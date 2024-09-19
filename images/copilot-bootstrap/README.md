# `copilot-bootstrap` Image

This image is used as a very light placeholder when deploying DBT Platform infrastructure. It allows us to get the infrastructure into a decent position before we start involving application code and all the variables that adds.

As it will almost never change, there is no automated build and publish at present, these are manual steps.

The image is published to `public.ecr.aws/uktrade/copilot-bootstrap:latest` in the `Tools` AWS account.

## Pingdom

To allow for the standard healthcheck endpoint `/pingdom/ping.xml`, this image uses a static XML file. 

This allows for the AWS Copilot configuration for health checks to be set prior to replacing the bootstrap image with an actual application. In addition, pingdom health checks can be created during the environment setup, allowing the migration team to be alerted should the to-be production environment experience issues.
