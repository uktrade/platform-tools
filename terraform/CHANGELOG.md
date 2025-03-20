# Changelog

## [7.5.0](https://github.com/uktrade/terraform-platform-modules/compare/7.4.0...7.5.0) (2025-03-07)


### Features

* DBTP-1688 adding multi-az and failover options for ElastiCache Redis HA plans ([#350](https://github.com/uktrade/terraform-platform-modules/issues/350)) ([5da529d](https://github.com/uktrade/terraform-platform-modules/commit/5da529db47c1d364c49dc4ad1e563aa9282f0aec))
* DBTP-1689 opensearch ha plan improvements ([#352](https://github.com/uktrade/terraform-platform-modules/issues/352)) ([38f852a](https://github.com/uktrade/terraform-platform-modules/commit/38f852a35335453a178015dcf93f5da97237e5fd))


### Bug Fixes

* DBTP-1804 - Pipeline resource names too long ([#343](https://github.com/uktrade/terraform-platform-modules/issues/343)) ([f3cf2b4](https://github.com/uktrade/terraform-platform-modules/commit/f3cf2b43041a62a5677890855898ff7c5d2e2267))
* DBTP-1818 - Fix failed pipeline notifications ([#354](https://github.com/uktrade/terraform-platform-modules/issues/354)) ([e81a8d6](https://github.com/uktrade/terraform-platform-modules/commit/e81a8d699c3e966fc16555aba7475b521eb87cfb))

## [7.4.0](https://github.com/uktrade/terraform-platform-modules/compare/7.3.1...7.4.0) (2025-02-28)


### Features

* dbtp-1769 cross aws account service to service connectivity ([#339](https://github.com/uktrade/terraform-platform-modules/issues/339)) ([7807d30](https://github.com/uktrade/terraform-platform-modules/commit/7807d307e4b62abb8268d2e0a2018ad5ea01e2f7))


### Bug Fixes

* DBTP-1563 - Use iam_role_policy instead of deprecated inline policies ([#347](https://github.com/uktrade/terraform-platform-modules/issues/347)) ([d146e73](https://github.com/uktrade/terraform-platform-modules/commit/d146e7371dde6b88f3b3c2a1b2f57dfac9c6b73c))
* Fix missing tag for SSM parameter EGRESS_IP ([#349](https://github.com/uktrade/terraform-platform-modules/issues/349)) ([8483746](https://github.com/uktrade/terraform-platform-modules/commit/84837468ddd86383306a68b15caacc4aa61bc4d0))

## [7.3.1](https://github.com/uktrade/terraform-platform-modules/compare/7.3.0...7.3.1) (2025-02-21)


### Bug Fixes

* DBTP-1700 Deprecate cross_enviroment_service_access application property ([#345](https://github.com/uktrade/terraform-platform-modules/issues/345)) ([bf431c6](https://github.com/uktrade/terraform-platform-modules/commit/bf431c6b4e38b41310818976c74f2cf6ad4cecff))

## [7.3.0](https://github.com/uktrade/terraform-platform-modules/compare/7.2.0...7.3.0) (2025-02-20)


### Features

* DBTP-1788 Add deploy_repository key ([#341](https://github.com/uktrade/terraform-platform-modules/issues/341)) ([8c44ce7](https://github.com/uktrade/terraform-platform-modules/commit/8c44ce784fbc22c0455f477b9b41d0b49ee85ca6))


### Bug Fixes

* DBTP-1746 - Allow CDN origin options to be updated ([#334](https://github.com/uktrade/terraform-platform-modules/issues/334)) ([51ee145](https://github.com/uktrade/terraform-platform-modules/commit/51ee145c21dc9686d65eb744a6ff0961b22823eb))
* DBTP-1789 - Remove required pipelines config ([#338](https://github.com/uktrade/terraform-platform-modules/issues/338)) ([4c76c94](https://github.com/uktrade/terraform-platform-modules/commit/4c76c946d2f50468d31597b81c64ca7a1492e001))
* DBTP-1803 - Failure to retrieve service name ([#340](https://github.com/uktrade/terraform-platform-modules/issues/340)) ([916843d](https://github.com/uktrade/terraform-platform-modules/commit/916843dc9df626027162d3b1d2d14c22e2dde0db))
* DBTP-1991 Allow environment pipeline to adjust ElastiCache replication count ([#335](https://github.com/uktrade/terraform-platform-modules/issues/335)) ([2052b95](https://github.com/uktrade/terraform-platform-modules/commit/2052b951f8fe0b655a07e66ab3ab3ede36e9ca23))
* Redis plans being ignored ([#344](https://github.com/uktrade/terraform-platform-modules/issues/344)) ([808748e](https://github.com/uktrade/terraform-platform-modules/commit/808748eb0d8fed6cb0edf524c8c2e8c09fe86616))

## [7.2.0](https://github.com/uktrade/terraform-platform-modules/compare/7.1.0...7.2.0) (2025-02-11)


### Features

* Add table to CloudWatch dashboard to show deployed images ([#328](https://github.com/uktrade/terraform-platform-modules/issues/328)) ([7eb3f2b](https://github.com/uktrade/terraform-platform-modules/commit/7eb3f2b95e43c89bffba0d05e333604132521689))


### Bug Fixes

* DBTP-1736 - Add custom slack channel id to image build project ([#326](https://github.com/uktrade/terraform-platform-modules/issues/326)) ([781b2f8](https://github.com/uktrade/terraform-platform-modules/commit/781b2f87a5adcf440f35bb561933e1c661ce4052))
* DBTP-1749 - Fix deploy status is null error ([#329](https://github.com/uktrade/terraform-platform-modules/issues/329)) ([430ff02](https://github.com/uktrade/terraform-platform-modules/commit/430ff02c90ef26d627b36001dde828fb25512b03))
* DBTP-1786 - Use service environment variable to get task count ([#332](https://github.com/uktrade/terraform-platform-modules/issues/332)) ([974e054](https://github.com/uktrade/terraform-platform-modules/commit/974e054cd1fd6598a537961ad13a4c817992cbfe))
* DBTP-1787 - Fix deploy repository name ([#330](https://github.com/uktrade/terraform-platform-modules/issues/330)) ([67e5394](https://github.com/uktrade/terraform-platform-modules/commit/67e5394ec3fbb7e7e5584ae22f1416ab362a8a64))

## [7.1.0](https://github.com/uktrade/terraform-platform-modules/compare/7.0.0...7.1.0) (2025-01-31)


### Features

* DBTP-1687 Reduce length of artifact and KMS key names ([#323](https://github.com/uktrade/terraform-platform-modules/issues/323)) ([0b5241b](https://github.com/uktrade/terraform-platform-modules/commit/0b5241b2e878692f4b3b9986492e44ba81b071d6))

## [7.0.0](https://github.com/uktrade/terraform-platform-modules/compare/6.1.0...7.0.0) (2025-01-28)


### ⚠ BREAKING CHANGES

* DBTP-1503 - Cross account deploy and manual release pipeline ([#306](https://github.com/uktrade/terraform-platform-modules/issues/306))

### Features

* DBTP-1503 - Cross account deploy and manual release pipeline ([#306](https://github.com/uktrade/terraform-platform-modules/issues/306)) ([7446c84](https://github.com/uktrade/terraform-platform-modules/commit/7446c84f9fc05b5c2e4ec81571ae7ffa1ae1fb14))

## [6.1.0](https://github.com/uktrade/terraform-platform-modules/compare/6.0.1...6.1.0) (2025-01-28)


### Features

* Support multiple source buckets for data migration ([#321](https://github.com/uktrade/terraform-platform-modules/issues/321)) ([49c2a4d](https://github.com/uktrade/terraform-platform-modules/commit/49c2a4daf3dd976f6bef8cce7a5724185a57c7cf))


### Bug Fixes

* Missing environment pipeline permissions ([#318](https://github.com/uktrade/terraform-platform-modules/issues/318)) ([155f371](https://github.com/uktrade/terraform-platform-modules/commit/155f3718917a4f6c09da0c5dd25d354eda5f2380))

## [6.0.1](https://github.com/uktrade/terraform-platform-modules/compare/6.0.0...6.0.1) (2025-01-21)


### Bug Fixes

* DBTP-1694 - Fix policy issues ([#316](https://github.com/uktrade/terraform-platform-modules/issues/316)) ([ec0733b](https://github.com/uktrade/terraform-platform-modules/commit/ec0733b380d27bfd6b93175e69640b0453abadb2))

## [6.0.0](https://github.com/uktrade/terraform-platform-modules/compare/5.15.0...6.0.0) (2025-01-09)


### ⚠ BREAKING CHANGES

* DBTP-1395 Add CloudFront and application load balancer origin verification secret for IP Filter spoofing ([#273](https://github.com/uktrade/terraform-platform-modules/issues/273))

### Features

* DBTP-1395 Add CloudFront and application load balancer origin verification secret for IP Filter spoofing ([#273](https://github.com/uktrade/terraform-platform-modules/issues/273)) ([7c182e0](https://github.com/uktrade/terraform-platform-modules/commit/7c182e002ffc2ad465dfef255c086af114e53e97))

## Upgrade Path

To upgrade to version 6 of terraform-platform-modules you can modify the 
`<application>-deploy/platform-config.yml` for the environments that you want to upgrade (put the `versions` property in an individual environment or under the `*` to apply to all environments)

```
  environments:
  "*":
    accounts:
      deploy:
        name: "platform-sandbox"
        id: "563763463626"
      dns:
        name: "dev"
        id: "011755346992"
    vpc: platform-sandbox-dev
  dev:
    versions:                        # add "versions" property
      terraform-platform-modules: 6  # set "terraform-platform-modules" property to 6
  ...
```

## [5.15.0](https://github.com/uktrade/terraform-platform-modules/compare/5.14.0...5.15.0) (2025-01-07)


### Features

* DBTP-1568 - Add s3 support for cross environment service access ([#293](https://github.com/uktrade/terraform-platform-modules/issues/293)) ([e4252ad](https://github.com/uktrade/terraform-platform-modules/commit/e4252addef2493c65735ced988d8c42ad3f66d7e))


### Bug Fixes

* Update deprecated managed role policy ([#305](https://github.com/uktrade/terraform-platform-modules/issues/305)) ([5e73422](https://github.com/uktrade/terraform-platform-modules/commit/5e73422305bf329eff0a7ef5db2274834b5158e1))

## [5.14.0](https://github.com/uktrade/terraform-platform-modules/compare/5.13.0...5.14.0) (2024-12-12)


### Features

* DBTP-1498 - Wrap database copy in pipeline ([#301](https://github.com/uktrade/terraform-platform-modules/issues/301)) ([917457d](https://github.com/uktrade/terraform-platform-modules/commit/917457df29c8867d06b38bce19a3bb0be24b067a))

## [5.13.0](https://github.com/uktrade/terraform-platform-modules/compare/5.12.1...5.13.0) (2024-12-11)


### Features

* Removing hardcoded value for S3 ENDPOINT ([#302](https://github.com/uktrade/terraform-platform-modules/issues/302)) ([cffd06a](https://github.com/uktrade/terraform-platform-modules/commit/cffd06ac1801190f3a4da38d8a252ac653ce95e6))

## [5.12.1](https://github.com/uktrade/terraform-platform-modules/compare/5.12.0...5.12.1) (2024-12-04)


### Bug Fixes

* Environment pipeline permissions ([#299](https://github.com/uktrade/terraform-platform-modules/issues/299)) ([7eb1a63](https://github.com/uktrade/terraform-platform-modules/commit/7eb1a63c5ffde9767ed9a71fd9739378fd56976d))

## [5.12.0](https://github.com/uktrade/terraform-platform-modules/compare/5.11.0...5.12.0) (2024-12-03)


### Features

* DBTP-1299 - Cross account database copy ([#294](https://github.com/uktrade/terraform-platform-modules/issues/294)) ([ac84ca8](https://github.com/uktrade/terraform-platform-modules/commit/ac84ca8690ab530e74efadabf179fa8b38059c70))

## [5.11.0](https://github.com/uktrade/terraform-platform-modules/compare/5.10.0...5.11.0) (2024-11-29)


### Features

* DBTP-1503 - Terraform codebase pipelines ([#276](https://github.com/uktrade/terraform-platform-modules/issues/276)) ([96b5935](https://github.com/uktrade/terraform-platform-modules/commit/96b593574db00c32c682726826ee765ebb561863))


### Bug Fixes

* Add missing environment pipeline permission ([#297](https://github.com/uktrade/terraform-platform-modules/issues/297)) ([57f4ea1](https://github.com/uktrade/terraform-platform-modules/commit/57f4ea11b6e99fef1f9d9b0a99c6a7085f463579))

## [5.10.0](https://github.com/uktrade/terraform-platform-modules/compare/5.9.0...5.10.0) (2024-11-26)


### Features

* DBTP-1568 - Add s3 support for external role access ([#292](https://github.com/uktrade/terraform-platform-modules/issues/292)) ([f20e203](https://github.com/uktrade/terraform-platform-modules/commit/f20e2034d5ec51d59d3cafbe679432b51867798e))

## [5.9.0](https://github.com/uktrade/terraform-platform-modules/compare/5.8.1...5.9.0) (2024-11-21)


### Features

* DBTP 1433 cdn cache on paths ([#291](https://github.com/uktrade/terraform-platform-modules/issues/291)) ([c456564](https://github.com/uktrade/terraform-platform-modules/commit/c4565641e91369c309bdec2adaf46127c9d5f6a4))
* DBTP-1380 Get Opensearch/Redis versions from AWS API - Permissions on env pipeline ([#275](https://github.com/uktrade/terraform-platform-modules/issues/275)) ([aca4cc4](https://github.com/uktrade/terraform-platform-modules/commit/aca4cc4dfe6a52f19a65cc3c107f0ca5500c19ba))

## [5.8.1](https://github.com/uktrade/terraform-platform-modules/compare/5.8.0...5.8.1) (2024-11-14)


### Bug Fixes

* DBTP-1534 Add S3MigrationRole to the resources allowed to add policies and roles ([#283](https://github.com/uktrade/terraform-platform-modules/issues/283)) ([0a4130e](https://github.com/uktrade/terraform-platform-modules/commit/0a4130ed37cb16a05ea8f1b6ddebe4d05b2d6183))

## [5.8.0](https://github.com/uktrade/terraform-platform-modules/compare/5.7.1...5.8.0) (2024-11-13)


### Features

* DBTP-1502 - Terraform image build codebuild project ([#274](https://github.com/uktrade/terraform-platform-modules/issues/274)) ([4f44598](https://github.com/uktrade/terraform-platform-modules/commit/4f44598c84b943c2056cd60a395790855e9beb24))


### Bug Fixes

* DBTP-1534 - Assume role policy for the S3 migration were too strict so relaxing them ([#279](https://github.com/uktrade/terraform-platform-modules/issues/279)) ([3ea79ff](https://github.com/uktrade/terraform-platform-modules/commit/3ea79ff7e9a825870c2c8d3638f464fc649892c5))

## [5.7.1](https://github.com/uktrade/terraform-platform-modules/compare/5.7.0...5.7.1) (2024-11-08)


### Bug Fixes

* Environment pipelines given ECS permissions for DatabaseCopy inf… ([#271](https://github.com/uktrade/terraform-platform-modules/issues/271)) ([1cd29ab](https://github.com/uktrade/terraform-platform-modules/commit/1cd29ab7f4955166656306d4a3086f707ebf314d))
* Environment pipelines given ECS permissions for DatabaseCopy infrastructure ([#267](https://github.com/uktrade/terraform-platform-modules/issues/267)) ([00babbd](https://github.com/uktrade/terraform-platform-modules/commit/00babbd4e00ba7c0820361b4b3aa7720fa82cc6d))
* Revert "fix: Environment pipelines given ECS permissions for Database..." ([#270](https://github.com/uktrade/terraform-platform-modules/issues/270)) ([d8ba1af](https://github.com/uktrade/terraform-platform-modules/commit/d8ba1af68c4314352ea440f0500edd4cfb69ef7a))

## [5.7.0](https://github.com/uktrade/terraform-platform-modules/compare/5.6.1...5.7.0) (2024-11-05)


### Features

* DBTP-1431 Allow setting custom timeouts on CloudFront ([#255](https://github.com/uktrade/terraform-platform-modules/issues/255)) ([d6539a5](https://github.com/uktrade/terraform-platform-modules/commit/d6539a5aca15233da9e1d2cd77ab775fdb4ee05c))

## [5.6.1](https://github.com/uktrade/terraform-platform-modules/compare/5.6.0...5.6.1) (2024-11-01)


### Bug Fixes

* DBTP-1454 Limit addons parameter to current environment ([#264](https://github.com/uktrade/terraform-platform-modules/issues/264)) ([d9b51d5](https://github.com/uktrade/terraform-platform-modules/commit/d9b51d530df74a5386b3ffc46c1132e14f37c7dc))

## [5.6.0](https://github.com/uktrade/terraform-platform-modules/compare/5.5.3...5.6.0) (2024-10-30)


### Features

* Add permissions to the database-load module to allow deletion of the … ([#249](https://github.com/uktrade/terraform-platform-modules/issues/249)) ([1f37adf](https://github.com/uktrade/terraform-platform-modules/commit/1f37adfdfbb427fe8151f86780eef2367d5756e2))


### Bug Fixes

* DBTP-1456 Stop the terraform tests GitHub Action excluding modules with submodules ([#262](https://github.com/uktrade/terraform-platform-modules/issues/262)) ([492d102](https://github.com/uktrade/terraform-platform-modules/commit/492d102f849b2cb58a48e38a897a6169d9d605c4))

## [5.5.3](https://github.com/uktrade/terraform-platform-modules/compare/5.5.2...5.5.3) (2024-10-29)


### Fixes

* DBTP-1495 Add some iam:UpdateAssumeRolePolicy permissions so that the deploy environment pipelines work. ([#260](https://github.com/uktrade/terraform-platform-modules/issues/260)) ([049cd4d](https://github.com/uktrade/terraform-platform-modules/commit/049cd4d5205565f55c00ccd427d5de929f2a1c16)))

## [5.5.2](https://github.com/uktrade/terraform-platform-modules/compare/5.5.1...5.5.2) (2024-10-25)


### Bug Fixes

* Add missing load balancer permission ([#256](https://github.com/uktrade/terraform-platform-modules/issues/256)) ([8c1357e](https://github.com/uktrade/terraform-platform-modules/commit/8c1357e8d600c03be6882efb0b6444ebe2bc02b2))
* DBTP-1435 Allow environment pipeline to update assume role policy on shared s3 role ([#250](https://github.com/uktrade/terraform-platform-modules/issues/250)) ([e9e12dd](https://github.com/uktrade/terraform-platform-modules/commit/e9e12ddb1f36aea1f8f4e7af8efd3230f2efffd1))

## [5.5.1](https://github.com/uktrade/terraform-platform-modules/compare/5.5.0...5.5.1) (2024-10-17)


### Bug Fixes

* Tighten ECR permissions ([#247](https://github.com/uktrade/terraform-platform-modules/issues/247)) ([2cbace7](https://github.com/uktrade/terraform-platform-modules/commit/2cbace7723363cba48bf9dd111472603d2be524e))

## [5.5.0](https://github.com/uktrade/terraform-platform-modules/compare/5.4.3...5.5.0) (2024-10-16)


### Features

* Enable data copy between VPCs in a single account ([#239](https://github.com/uktrade/terraform-platform-modules/issues/239)) ([3329381](https://github.com/uktrade/terraform-platform-modules/commit/332938139752b0c46674fcb4abfcc154f6922672))

## [5.4.3](https://github.com/uktrade/terraform-platform-modules/compare/5.4.2...5.4.3) (2024-10-04)


### Bug Fixes

* DBTP-1398 Correct prod domain name for static content S3 buckets ([#241](https://github.com/uktrade/terraform-platform-modules/issues/241)) ([33c6e57](https://github.com/uktrade/terraform-platform-modules/commit/33c6e57fd8264c1225cabcbdb2fd6d4e03a52a06))
* DBTP-1398 Correct prod domain name for static content S3 buckets (2nd pass) ([#243](https://github.com/uktrade/terraform-platform-modules/issues/243)) ([f711fac](https://github.com/uktrade/terraform-platform-modules/commit/f711fac6c1291638a9847cec3ffef752c101aed2))

## [5.4.2](https://github.com/uktrade/terraform-platform-modules/compare/5.4.1...5.4.2) (2024-09-26)


### Bug Fixes

* DBTP-1383 - Set correct central log subscription filter destinations ([#233](https://github.com/uktrade/terraform-platform-modules/issues/233)) ([2b57276](https://github.com/uktrade/terraform-platform-modules/commit/2b5727604f40cce9c109e6d6f62d3eda256b38e9))

## [5.4.1](https://github.com/uktrade/terraform-platform-modules/compare/5.4.0...5.4.1) (2024-09-26)


### Bug Fixes

* DBTP-1391 - Create separate pipeline artifact bucket ([#234](https://github.com/uktrade/terraform-platform-modules/issues/234)) ([c3d5bbc](https://github.com/uktrade/terraform-platform-modules/commit/c3d5bbc73d5da2bfb22fe2b601a1b453d1996d15))
* DBTP-1394 - Fix platform-helper environment generate command in environment pipeline apply stage ([#236](https://github.com/uktrade/terraform-platform-modules/issues/236)) ([f0b7bc1](https://github.com/uktrade/terraform-platform-modules/commit/f0b7bc11c670d21dced8400d4bd8a0e0c8591e6d))
* DBTP-1396 - Fix S3 domain name for prod environments ([#237](https://github.com/uktrade/terraform-platform-modules/issues/237)) ([0df571a](https://github.com/uktrade/terraform-platform-modules/commit/0df571af24307bd2525445b02b47d0e41ef7e866))

## [5.4.0](https://github.com/uktrade/terraform-platform-modules/compare/5.3.0...5.4.0) (2024-09-18)


### Features

* Dbtp 1162 support hosting static sites on s3 ([#212](https://github.com/uktrade/terraform-platform-modules/issues/212)) ([f1976bb](https://github.com/uktrade/terraform-platform-modules/commit/f1976bb694d598bd175003c475e5fa779bd80b65))


### Bug Fixes

* DBTP-1338 - Run copilot env deploy in env pipelines ([#224](https://github.com/uktrade/terraform-platform-modules/issues/224)) ([ea3b56d](https://github.com/uktrade/terraform-platform-modules/commit/ea3b56d3f86676eec487dc1b65aba2c387f22594))
* DBTP-1366 - Force environment pipeline to trigger on correct branch ([#230](https://github.com/uktrade/terraform-platform-modules/issues/230)) ([3a95838](https://github.com/uktrade/terraform-platform-modules/commit/3a958381bae3fc911abfcf124c0df3ab3765ca15))

## [5.3.0](https://github.com/uktrade/terraform-platform-modules/compare/5.2.4...5.3.0) (2024-09-10)


### Features

* DBTP-1301 - provide cross account s3 to s3 migration permissions ([#220](https://github.com/uktrade/terraform-platform-modules/issues/220)) ([85c7f46](https://github.com/uktrade/terraform-platform-modules/commit/85c7f467b560d5140eccc68f325ddbe14465df05))

## [5.2.4](https://github.com/uktrade/terraform-platform-modules/compare/5.2.3...5.2.4) (2024-09-05)


### Bug Fixes

* DBTP-1346 Add special characters & urlencode options for OpenSearch passwords ([#225](https://github.com/uktrade/terraform-platform-modules/issues/225)) ([d11bd13](https://github.com/uktrade/terraform-platform-modules/commit/d11bd13cf3f049db5e05e43b43d9fc6b5f839ce3))

## [5.2.3](https://github.com/uktrade/terraform-platform-modules/compare/5.2.2...5.2.3) (2024-09-02)


### Bug Fixes

* hardcoded 'demodjango' ([#221](https://github.com/uktrade/terraform-platform-modules/issues/221)) ([d0910aa](https://github.com/uktrade/terraform-platform-modules/commit/d0910aaa52738f6e3c855eb54c8e81cc45866f13))

## [5.2.2](https://github.com/uktrade/terraform-platform-modules/compare/5.2.1...5.2.2) (2024-08-23)


### Bug Fixes

* No idea why this was working before but isn't now. ([#218](https://github.com/uktrade/terraform-platform-modules/issues/218)) ([253bab5](https://github.com/uktrade/terraform-platform-modules/commit/253bab587df9d1feb7d0b51604d120937cb5fedf))

## [5.2.1](https://github.com/uktrade/terraform-platform-modules/compare/5.2.0...5.2.1) (2024-08-22)


### Bug Fixes

* Fix missing quote and missing permission ([#216](https://github.com/uktrade/terraform-platform-modules/issues/216)) ([9f7992c](https://github.com/uktrade/terraform-platform-modules/commit/9f7992c6790ee54130a865570efcbea2acdb7005))

## [5.2.0](https://github.com/uktrade/terraform-platform-modules/compare/5.1.6...5.2.0) (2024-08-21)


### Features

* Changes to buildspec to support changing the version of platform-helper used in the pipeline ([#206](https://github.com/uktrade/terraform-platform-modules/issues/206)) ([1d20161](https://github.com/uktrade/terraform-platform-modules/commit/1d20161752182d47440fe8e0f12be251152516bc))

## [5.1.6](https://github.com/uktrade/terraform-platform-modules/compare/5.1.5...5.1.6) (2024-08-20)


### Bug Fixes

* DBTP-1304 - manage users lambda does not drop tables ([#207](https://github.com/uktrade/terraform-platform-modules/issues/207)) ([aa3b567](https://github.com/uktrade/terraform-platform-modules/commit/aa3b5676adc119bf0d4dfad925cf0855422bee44))

## [5.1.5](https://github.com/uktrade/terraform-platform-modules/compare/5.1.4...5.1.5) (2024-08-19)


### Bug Fixes

* DBTP-972 Add IAM Permissions for Pipeline Changes ([#209](https://github.com/uktrade/terraform-platform-modules/issues/209)) ([71992ac](https://github.com/uktrade/terraform-platform-modules/commit/71992acb579c29ebfb59de37308b0b556847b56c))

## [5.1.4](https://github.com/uktrade/terraform-platform-modules/compare/5.1.3...5.1.4) (2024-08-19)


### Bug Fixes

* DBTP-972 Ignored by Checkov baseline ([#190](https://github.com/uktrade/terraform-platform-modules/issues/190)) ([1564260](https://github.com/uktrade/terraform-platform-modules/commit/15642606a89adc2ef9a9c9df7fc9b55bf61f951e))

## [5.1.3](https://github.com/uktrade/terraform-platform-modules/compare/5.1.2...5.1.3) (2024-08-15)


### Bug Fixes

* buildspec notify command ADDITIONAL_OPTIONS injection ([#204](https://github.com/uktrade/terraform-platform-modules/issues/204)) ([a9597ba](https://github.com/uktrade/terraform-platform-modules/commit/a9597baf0d7984500fc6c3e0548e4446e59a95eb))

## [5.1.2](https://github.com/uktrade/terraform-platform-modules/compare/5.1.1...5.1.2) (2024-08-15)


### Bug Fixes

* cdn and application-load-balancer modules "null value cannot be used as the collection in a 'for' expression" error ([#202](https://github.com/uktrade/terraform-platform-modules/issues/202)) ([690f030](https://github.com/uktrade/terraform-platform-modules/commit/690f03039d8a0d0631360acbcd36856865b8efa4))

## [5.1.1](https://github.com/uktrade/terraform-platform-modules/compare/5.1.0...5.1.1) (2024-08-14)


### Bug Fixes

* Add elastic load balancer modify permission for pipeline  ([#200](https://github.com/uktrade/terraform-platform-modules/issues/200)) ([936270c](https://github.com/uktrade/terraform-platform-modules/commit/936270ced78bb22a0fb6cc09adfca605fe44b182))
* DBTP-1169 Added Validation for Domain Name Length ([#198](https://github.com/uktrade/terraform-platform-modules/issues/198)) ([39b33cc](https://github.com/uktrade/terraform-platform-modules/commit/39b33cc261cbc40a82d9548d79e00a2ebdc2e2f6))

## [5.1.0](https://github.com/uktrade/terraform-platform-modules/compare/5.0.1...5.1.0) (2024-08-08)


### Features

* DBTP-1137 trigger prod pipeline from non-prod pipeline ([#195](https://github.com/uktrade/terraform-platform-modules/issues/195)) ([d350039](https://github.com/uktrade/terraform-platform-modules/commit/d3500394a8035cc94221dee4de0a48e1bccc42b7))


### Bug Fixes

* DBTP-1143 Prevent Trigger Being Deleted on TF Plan/Apply ([#193](https://github.com/uktrade/terraform-platform-modules/issues/193)) ([9e7c870](https://github.com/uktrade/terraform-platform-modules/commit/9e7c8703745be0d1221b55b4b8af9567e0240614))
* DBTP-1149 - Cancel Outstanding Approval Requests before Performing a Terraform Plan ([#196](https://github.com/uktrade/terraform-platform-modules/issues/196)) ([afb1829](https://github.com/uktrade/terraform-platform-modules/commit/afb1829c28d22e01358a388f55de7f457640aadf))

## [5.0.1](https://github.com/uktrade/terraform-platform-modules/compare/5.0.0...5.0.1) (2024-07-18)


### Bug Fixes

* DBTP-1128 - Connection Error when trying to connect to Redis via Conduit ([#184](https://github.com/uktrade/terraform-platform-modules/issues/184)) ([65cc75d](https://github.com/uktrade/terraform-platform-modules/commit/65cc75deae092f0287a32daa7119069c880dffc4))
* DBTP-1128 Allow Pipeline Account to Create IAM Roles ([#189](https://github.com/uktrade/terraform-platform-modules/issues/189)) ([f95d923](https://github.com/uktrade/terraform-platform-modules/commit/f95d923dcf950350dda822b097f5ff25783f0adf))

## [5.0.0](https://github.com/uktrade/terraform-platform-modules/compare/4.2.0...5.0.0) (2024-07-12)


### ⚠ BREAKING CHANGES

* DBTP-1072 Change ADDITIONAL_IP_LIST to EGRESS_IPS ([#179](https://github.com/uktrade/terraform-platform-modules/issues/179))

### Features

* Removing all copilot commands from the terraform pipelines ([#185](https://github.com/uktrade/terraform-platform-modules/issues/185)) ([68506bc](https://github.com/uktrade/terraform-platform-modules/commit/68506bcc541b349285dc3f63b5a02b2ab8a3e5a2))


### Bug Fixes

* DBTP-1166 - Fix failing e2e tests ([#183](https://github.com/uktrade/terraform-platform-modules/issues/183)) ([d09a696](https://github.com/uktrade/terraform-platform-modules/commit/d09a6965499748edf38e67624247306129499cb8))


### Miscellaneous Chores

* DBTP-1072 Change ADDITIONAL_IP_LIST to EGRESS_IPS ([#179](https://github.com/uktrade/terraform-platform-modules/issues/179)) ([0db3962](https://github.com/uktrade/terraform-platform-modules/commit/0db39629412f4c75c437f91b072a09b7358b3718))

## [4.2.0](https://github.com/uktrade/terraform-platform-modules/compare/4.1.0...4.2.0) (2024-07-05)


### Features

* DBTP-1116 - support configurable backup_retention_period for postgres DB ([#173](https://github.com/uktrade/terraform-platform-modules/issues/173)) ([53afce8](https://github.com/uktrade/terraform-platform-modules/commit/53afce8dbfe524b423043e933980351d63acfdf0))

## [4.1.0](https://github.com/uktrade/terraform-platform-modules/compare/4.0.0...4.1.0) (2024-07-03)


### Features

* DBTP-1040 support s3 lifecycle policy ([#168](https://github.com/uktrade/terraform-platform-modules/issues/168)) ([73aa377](https://github.com/uktrade/terraform-platform-modules/commit/73aa3777b99e49564393b5e170ea5522fd593ad0))


### Bug Fixes

* DBTP-1040 - filter_prefix terraform variable is optional ([#178](https://github.com/uktrade/terraform-platform-modules/issues/178)) ([d0c5a00](https://github.com/uktrade/terraform-platform-modules/commit/d0c5a00fbbffe67c6a9d88c7f9f1de2d937e648b))

## [4.0.0](https://github.com/uktrade/terraform-platform-modules/compare/3.0.0...4.0.0) (2024-07-01)


### ⚠ BREAKING CHANGES

* DBTP-958 Straighten up Postgres plans (replay) ([#135](https://github.com/uktrade/terraform-platform-modules/issues/135))

### Features

* DBTP-1072 As a developer, when I create an API and a frontend service in the same environment and put the frontend service behind the IP Filter, I want the front end service to be able to access the api ([#165](https://github.com/uktrade/terraform-platform-modules/issues/165)) ([4bcce04](https://github.com/uktrade/terraform-platform-modules/commit/4bcce0421e5a3f305ec5384b8b0987f49ec1113a))
* DBTP-958 Straighten up Postgres plans (replay) ([#135](https://github.com/uktrade/terraform-platform-modules/issues/135)) ([1d566f1](https://github.com/uktrade/terraform-platform-modules/commit/1d566f13c6184caf7f73a770457f08affd0c7739))


### Bug Fixes

* Add ListCertificates permission ([#170](https://github.com/uktrade/terraform-platform-modules/issues/170)) ([4f53a0c](https://github.com/uktrade/terraform-platform-modules/commit/4f53a0c120940f633d80392423afd7654d702e65))
* DBTP-1089 Move to shared log resource policy ([#166](https://github.com/uktrade/terraform-platform-modules/issues/166)) ([9527e75](https://github.com/uktrade/terraform-platform-modules/commit/9527e75131d001ca6ed52e3dd4d1268e2701eea5))
* DBTP-1104 Ensure Terraform plan resources are available during apply stage. ([#174](https://github.com/uktrade/terraform-platform-modules/issues/174)) ([7d2b397](https://github.com/uktrade/terraform-platform-modules/commit/7d2b397099ba327414bde68c28727d5338a0fa35))
* Don't generate environment Terraform manifest for demodjango toolspr ([#172](https://github.com/uktrade/terraform-platform-modules/issues/172)) ([f57b122](https://github.com/uktrade/terraform-platform-modules/commit/f57b122a3ef05557ddccab146bb166def492902a))
* Missing IAM permissions for pipeline to modify database ([#176](https://github.com/uktrade/terraform-platform-modules/issues/176)) ([33cd536](https://github.com/uktrade/terraform-platform-modules/commit/33cd5360afd4204b5ea43333834c13bf33a01708))

## [3.0.0](https://github.com/uktrade/terraform-platform-modules/compare/2.3.0...3.0.0) (2024-06-21)


### ⚠ BREAKING CHANGES

* New config file and support for multiple pipelines ([#159](https://github.com/uktrade/terraform-platform-modules/issues/159))

### Features

* New config file and support for multiple pipelines ([#159](https://github.com/uktrade/terraform-platform-modules/issues/159)) ([4399fc9](https://github.com/uktrade/terraform-platform-modules/commit/4399fc9ae2b25612ef06ca4bd1ae2938dcfdc944))

## [2.3.0](https://github.com/uktrade/terraform-platform-modules/compare/2.2.1...2.3.0) (2024-06-20)


### Features

* DBTP-946 vpc store nat egress ips in parameter store ([#157](https://github.com/uktrade/terraform-platform-modules/issues/157)) ([2a7b595](https://github.com/uktrade/terraform-platform-modules/commit/2a7b59512880bb555d8dc8fc9e5be9987ed6f6f4))


### Bug Fixes

* add prometheus-policy to plans.yml ([#163](https://github.com/uktrade/terraform-platform-modules/issues/163)) ([d98d468](https://github.com/uktrade/terraform-platform-modules/commit/d98d468aa50fd44e71796c02df00680e393da658))

## [2.2.1](https://github.com/uktrade/terraform-platform-modules/compare/2.2.0...2.2.1) (2024-06-14)


### Bug Fixes

* make readonly lambda invocation depend on app user invocation ([#160](https://github.com/uktrade/terraform-platform-modules/issues/160)) ([1e0fe0d](https://github.com/uktrade/terraform-platform-modules/commit/1e0fe0d19792049ceccd6f6326620e85e13480f1))

## [2.2.0](https://github.com/uktrade/terraform-platform-modules/compare/2.1.0...2.2.0) (2024-06-06)


### Features

* dbtp-928 option to disable cdn ([#155](https://github.com/uktrade/terraform-platform-modules/issues/155)) ([e86fd89](https://github.com/uktrade/terraform-platform-modules/commit/e86fd8900b7372c47d3859ce0b236c40eb04a285))

## [2.1.0](https://github.com/uktrade/terraform-platform-modules/compare/2.0.0...2.1.0) (2024-06-04)


### Features

* Pipeline slack alerts ([#150](https://github.com/uktrade/terraform-platform-modules/issues/150)) ([ead58f3](https://github.com/uktrade/terraform-platform-modules/commit/ead58f39b6faecd8ffcd9fb18cc607416d20770b))


### Bug Fixes

* Fixed extensions module that was broken on the cdn declaration ([#152](https://github.com/uktrade/terraform-platform-modules/issues/152)) ([c76ac9f](https://github.com/uktrade/terraform-platform-modules/commit/c76ac9f2aedf06bdb35db6c7615b4770d6e7c2b0))

## [2.0.0](https://github.com/uktrade/terraform-platform-modules/compare/1.5.0...2.0.0) (2024-06-04)


### ⚠ BREAKING CHANGES

* DBTP-928 Add CDN endpoint module ([#141](https://github.com/uktrade/terraform-platform-modules/issues/141))

### Features

* DBTP-928 Add CDN endpoint module ([#141](https://github.com/uktrade/terraform-platform-modules/issues/141)) ([20d6f5b](https://github.com/uktrade/terraform-platform-modules/commit/20d6f5b9d25c2a94bb02d38ad862a5fa5fb9f224))

## [1.5.0](https://github.com/uktrade/terraform-platform-modules/compare/1.4.0...1.5.0) (2024-05-31)

### Features

* DBTP-434 Add Redis endpoint with ssl_cert_reqs parameter ([#147](https://github.com/uktrade/terraform-platform-modules/issues/147)) ([f7470e8](https://github.com/uktrade/terraform-platform-modules/commit/f7470e821c262de4ce50b0f1ebb30563ce145c88))

### Bug Fixes

* DBTP-1010 Readonly postgres user doesn't have read perms ([#140](https://github.com/uktrade/terraform-platform-modules/issues/140)) ([1628440](https://github.com/uktrade/terraform-platform-modules/commit/1628440ab653a27ecc205cad4a32750cf7a22b62))
* DBTP-944 Correct Redis tags ([#147](https://github.com/uktrade/terraform-platform-modules/issues/147)) ([f7470e8](https://github.com/uktrade/terraform-platform-modules/commit/f7470e821c262de4ce50b0f1ebb30563ce145c88))

## [1.4.0](https://github.com/uktrade/terraform-platform-modules/compare/1.3.0...1.4.0) (2024-05-30)


### Features

* Enable Intelligent-Tiering to allow parameters with &gt; 4096 characters ([#139](https://github.com/uktrade/terraform-platform-modules/issues/139)) ([9be7595](https://github.com/uktrade/terraform-platform-modules/commit/9be7595e491a50fa65aebdc38e99494880b559a5))


### Bug Fixes

* DBTP-1010 Readonly postgres user doesn't have read perms ([#140](https://github.com/uktrade/terraform-platform-modules/issues/140)) ([1628440](https://github.com/uktrade/terraform-platform-modules/commit/1628440ab653a27ecc205cad4a32750cf7a22b62))
* DBTP-998 - Move pipeline to platform-sandbox ([#137](https://github.com/uktrade/terraform-platform-modules/issues/137)) ([e97dcd4](https://github.com/uktrade/terraform-platform-modules/commit/e97dcd41c8face3e5dbbf1be1aa367b5c6861057))

## [1.3.0](https://github.com/uktrade/terraform-platform-modules/compare/1.2.2...1.3.0) (2024-05-23)


### Features

* Changed to new assume role name ([#128](https://github.com/uktrade/terraform-platform-modules/issues/128)) ([ca17b44](https://github.com/uktrade/terraform-platform-modules/commit/ca17b44a867245fc527d0a577823fde517a994a9))
* DBTP-909 - Run `copilot env deploy` in pipeline ([#126](https://github.com/uktrade/terraform-platform-modules/issues/126)) ([15abc7b](https://github.com/uktrade/terraform-platform-modules/commit/15abc7b37d7c5a8eee70a38be7c8c076df2084df))
* DBTP-914 - Environment pipeline terraform apply ([#116](https://github.com/uktrade/terraform-platform-modules/issues/116)) ([a7f701c](https://github.com/uktrade/terraform-platform-modules/commit/a7f701c6f0fbe94ec34a715fdcbcf173b5214391))
* Make ``platform-helper copilot make-addons` run in the pipeline ([#125](https://github.com/uktrade/terraform-platform-modules/issues/125)) ([2da6d2e](https://github.com/uktrade/terraform-platform-modules/commit/2da6d2e1d5fe66c0ada7a97a2496ea72b10cef7d))


### Bug Fixes

* add default volume size for rds local variable ([#124](https://github.com/uktrade/terraform-platform-modules/issues/124)) ([92bdd32](https://github.com/uktrade/terraform-platform-modules/commit/92bdd32fc6fea68a7f67f82fd26ecd2972564f0b))
* Dbtp 1016 update kms key alias name ([#131](https://github.com/uktrade/terraform-platform-modules/issues/131)) ([485792f](https://github.com/uktrade/terraform-platform-modules/commit/485792f1bfea2a0eb1a21be06a7f4f098f7a7b99))
* DBTP-958 Straighten up Postgres plans ([#112](https://github.com/uktrade/terraform-platform-modules/issues/112)) ([e15e12d](https://github.com/uktrade/terraform-platform-modules/commit/e15e12de752d560a03d68e77d70a5fd826e96a07))


## [1.2.2](https://github.com/uktrade/terraform-platform-modules/compare/1.2.1...1.2.2) (2024-05-14)


### Bug Fixes

* dbtp-971 add rollback option for HA OS ([#117](https://github.com/uktrade/terraform-platform-modules/issues/117)) ([d742850](https://github.com/uktrade/terraform-platform-modules/commit/d742850813e6d66f992f78dd2a98695e5cea60c2))

## [1.2.1](https://github.com/uktrade/terraform-platform-modules/compare/1.2.0...1.2.1) (2024-05-07)


### Bug Fixes

* DBTP 951 fix prod prod cert bug ([#113](https://github.com/uktrade/terraform-platform-modules/issues/113)) ([38cb5e0](https://github.com/uktrade/terraform-platform-modules/commit/38cb5e0ebd6856de4626f1804479000668ac51a0))

## [1.2.0](https://github.com/uktrade/terraform-platform-modules/compare/1.1.0...1.2.0) (2024-05-03)


### Features

* 872 checkov baseline file ([#109](https://github.com/uktrade/terraform-platform-modules/issues/109)) ([975fa06](https://github.com/uktrade/terraform-platform-modules/commit/975fa066fe62304d4981b81cd370468fb14a8ac3))
* DBTP-910 - Environment log resource policy overrides ([#95](https://github.com/uktrade/terraform-platform-modules/issues/95)) ([fa64beb](https://github.com/uktrade/terraform-platform-modules/commit/fa64beb3a84d3eeb93d5a7bbe5916b6bec17c4ec))
* DBTP-911 Barebones environment pipeline module ([#81](https://github.com/uktrade/terraform-platform-modules/issues/81)) ([10a65ab](https://github.com/uktrade/terraform-platform-modules/commit/10a65ab2f9699193a55eebcfc3415886c781fd20))
* DBTP-913 - Run terraform plan in environment pipelines ([#110](https://github.com/uktrade/terraform-platform-modules/issues/110)) ([a66f04a](https://github.com/uktrade/terraform-platform-modules/commit/a66f04ab4d4ddfde269406241ad79ea352175d16))


### Bug Fixes

* DBTP-839 Add tags for monitoring resources ([#102](https://github.com/uktrade/terraform-platform-modules/issues/102)) ([5f56af5](https://github.com/uktrade/terraform-platform-modules/commit/5f56af5e6ced9d5b39f460d7a8eb70fcd2932dab))
* DBTP-931 Fix OpenSearch tests ([#98](https://github.com/uktrade/terraform-platform-modules/issues/98)) ([3267c5b](https://github.com/uktrade/terraform-platform-modules/commit/3267c5b8e1b9d06f8c6a18cbb8fd73217655b1d7))
* DBTP-951 add prod check for additional address list ([#111](https://github.com/uktrade/terraform-platform-modules/issues/111)) ([53c9639](https://github.com/uktrade/terraform-platform-modules/commit/53c963902d9586b7b95ed5d1e2b42fd920f5c740))

## [1.1.0](https://github.com/uktrade/terraform-platform-modules/compare/1.0.0...1.1.0) (2024-04-19)


### Features

* DBTP 843 vpc peering ([#83](https://github.com/uktrade/terraform-platform-modules/issues/83)) ([3684d87](https://github.com/uktrade/terraform-platform-modules/commit/3684d877bf631a19aaf214dee330c55f3a42c0fb))
* DBTP-892 release-please to automate releases/tagging ([#89](https://github.com/uktrade/terraform-platform-modules/issues/89)) ([a8d4754](https://github.com/uktrade/terraform-platform-modules/commit/a8d4754baf2de1d18e3d8ddedb90133627240383))


### Bug Fixes

* Add domain provider alias to extensions unit test ([#86](https://github.com/uktrade/terraform-platform-modules/issues/86)) ([4a62675](https://github.com/uktrade/terraform-platform-modules/commit/4a62675df58a522717ec93a16fddcc42c0e8e3df))
* DBTP-896 - invalid opensearch config ([#73](https://github.com/uktrade/terraform-platform-modules/issues/73)) ([7e30b05](https://github.com/uktrade/terraform-platform-modules/commit/7e30b05036c2b3281ce28f58feaa1957c7c281a2))
* Parameterised account ID in unit test to allow tests to run in other accounts ([#84](https://github.com/uktrade/terraform-platform-modules/issues/84)) ([cec7852](https://github.com/uktrade/terraform-platform-modules/commit/cec7852be7c7e73393fb34b15a1b53eecb4a5ec5))
