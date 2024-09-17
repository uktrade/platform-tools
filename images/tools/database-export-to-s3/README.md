# Database Export to S3

## Overview

This image was designed to be run by an AWS Copilot scheduled Job.
The destination S3 bucket can reside in the same AWS account or be in a different AWS account.
It is assumed that the IAM role assigned to the scheduled job will have the required permissions to push objects into the destination bucket.

This image is based on [`public.ecr.aws/docker/library/debian:12-slim`](https://gallery.ecr.aws/debian/debian)
and installs the required tooling to connect to Postgres and S3.

The entrypoint.sh shell script is executed when the job starts. The container is destroyed when the job has completed.

## Required environment variables

- DESTINATION_S3_URI 
 
    e.g. s3://some-bucket
 
 
- DATABASE_CONNECTION_DETAILS
 
    e.g. {
         "username": "application_user", 
         "password": "top-secret", 
         "engine": "postgres", 
         "port": 5432,
         "dbname": "main",
         "host": "some-application-prod-important-db.cdgzzzs7777o.eu-west-2.rds.amazonaws.com", 
         "dbInstanceIdentifier": "db-29labcdefghijklmnopqrstuvw"
        }

## Publishing manually

Requires:

- [`docker`](https://www.docker.com)
- [`aws` CLI](https://aws.amazon.com/cli/)

From this image directory:

1. `aws sso login`
2. `aws ecr-public get-login-password --region eu-west-2 | docker login --username AWS --password-stdin public.ecr.aws/uktrade`
3. `docker build -t public.ecr.aws/uktrade/tunnel:database-export-to-s3 .`
4. `docker tag public.ecr.aws/uktrade/tunnel:database-export-to-s3 public.ecr.aws/uktrade/tunnel:database-export-to-s3-$(git rev-parse --short HEAD)`
5. `docker push public.ecr.aws/uktrade/tunnel:database-export-to-s3`
6. `docker push public.ecr.aws/uktrade/tunnel:database-export-to-s3-$(git rev-parse --short HEAD)`
7. `docker logout public.ecr.aws/uktrade`