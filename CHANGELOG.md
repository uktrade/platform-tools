# Changelog

## [11.2.0](https://github.com/uktrade/platform-tools/compare/11.1.0...11.2.0) (2024-11-04)


### Features

* DBTP-1071 Generate terraform config for environment pipeline ([#611](https://github.com/uktrade/platform-tools/issues/611)) ([237fb35](https://github.com/uktrade/platform-tools/commit/237fb35fe06df7fd13e93419d282dc067187d952))
* DBTP-1380/DBT-1393 validate Redis and OpenSearch versions are valid and supported versions ([#599](https://github.com/uktrade/platform-tools/issues/599)) ([e36deb2](https://github.com/uktrade/platform-tools/commit/e36deb2d9741907fedae3f2b1928ac6fc49f374e))


### Reverts

* "feat: DBTP-1380/DBT-1393 validate Redis and OpenSearch versions are valid and supported versions" ([#617](https://github.com/uktrade/platform-tools/issues/617)) ([6175a52](https://github.com/uktrade/platform-tools/commit/6175a5218474ecbe91d2d1746ffbfe7c99fe3990))


### Documentation

* Call out the offline command fix in the changelog ([#613](https://github.com/uktrade/platform-tools/issues/613)) ([e2a6396](https://github.com/uktrade/platform-tools/commit/e2a63961260d3b60a1ae9aa99a1bd06927e98ae9))

## [11.1.0](https://github.com/uktrade/platform-tools/compare/11.0.1...11.1.0) (2024-10-30)


### Features

* DBTP-1159 Add validation for duplicate entries in platform-config.yml ([#604](https://github.com/uktrade/platform-tools/issues/604)) ([d00e143](https://github.com/uktrade/platform-tools/commit/d00e143ecaa9e86645563d996ed79779cae52597))
* DBTP-1215 Improve error message when AWS profile not set ([#607](https://github.com/uktrade/platform-tools/issues/607)) ([beb0e7f](https://github.com/uktrade/platform-tools/commit/beb0e7f12013f035a1ffe2796a22b2a1bc70ed5f))
* Delete data dump from S3 after data load has been successful ([#600](https://github.com/uktrade/platform-tools/issues/600)) ([410cd56](https://github.com/uktrade/platform-tools/commit/410cd5673eccce5855d03b4f0cbb4d6c1377085a))


### Bug Fixes

* Fix issue with offline command resulting in 'CreateRule operation: Priority '100' is currently in use' error


### Documentation

* Add a note about regression/integration testing to the README.md ([#612](https://github.com/uktrade/platform-tools/issues/612)) ([d219356](https://github.com/uktrade/platform-tools/commit/d219356e41efb3b6eab3950a921aaf6e5b3b7d9c))

## [11.0.1](https://github.com/uktrade/platform-tools/compare/11.0.0...11.0.1) (2024-10-22)


### Bug Fixes

* Update dependencies ([#602](https://github.com/uktrade/platform-tools/issues/602)) ([a07050b](https://github.com/uktrade/platform-tools/commit/a07050b9cad2cf5e6eb0b4966c086e8a7996cce9))

## [11.0.0](https://github.com/uktrade/platform-tools/compare/10.11.3...11.0.0) (2024-10-16)


### ⚠ BREAKING CHANGES

* Implement a data copy command that copies data cross-VPC ([#565](https://github.com/uktrade/platform-tools/issues/565))

NOTE: This removes the previous `platform-helper database copy` command. Instructions for use of the replacement `dump` and `load` commands can be found here: https://platform.readme.trade.gov.uk/reference/copy-a-database-between-environments/

### Features

* DBTP-1110 support cdn configuration ([#596](https://github.com/uktrade/platform-tools/issues/596)) ([fd73517](https://github.com/uktrade/platform-tools/commit/fd73517512e1769285874dc3ca340dc4ebd8eefb))
* Implement a data copy command that copies data cross-VPC ([#565](https://github.com/uktrade/platform-tools/issues/565)) ([d9037e5](https://github.com/uktrade/platform-tools/commit/d9037e5f32071c7a6ed41dc4d1e697a3bd44b40e))

## [10.11.3](https://github.com/uktrade/platform-tools/compare/10.11.2...10.11.3) (2024-10-02)


### Bug Fixes

* DBTP-1373 - Handle SchemaErrors from platform config validation gracefully ([#584](https://github.com/uktrade/platform-tools/issues/584)) ([8324049](https://github.com/uktrade/platform-tools/commit/83240491fede3130c5c4d338029bb139bf7d2ef0))
* DBTP-1375 - platform helper version get-platform-helper-for-project no longer validates config ([#575](https://github.com/uktrade/platform-tools/issues/575)) ([f62c25d](https://github.com/uktrade/platform-tools/commit/f62c25d5fcb218c1668be1a7043ca45745c7c03b))
* fix typo ([#591](https://github.com/uktrade/platform-tools/issues/591)) ([8f48dd3](https://github.com/uktrade/platform-tools/commit/8f48dd3dc6449045add87215483a625290b21484))

## [10.11.2](https://github.com/uktrade/platform-tools/compare/10.11.1...10.11.2) (2024-09-26)


### Bug Fixes

* DBTP-1382 Fix conduit session KMS access permissions ([#583](https://github.com/uktrade/platform-tools/issues/583)) ([fc3051e](https://github.com/uktrade/platform-tools/commit/fc3051e4c9591a0a87cc28dab7f413ca4acde9c1))
* Restrict regression test alerts to toolspr environment ([#581](https://github.com/uktrade/platform-tools/issues/581)) ([d40f50f](https://github.com/uktrade/platform-tools/commit/d40f50fb9c8b4c552f223e97b31454e3afc302d7))

## [10.11.1](https://github.com/uktrade/platform-tools/compare/10.11.0...10.11.1) (2024-09-24)


### Bug Fixes

* DBTP-1392 Allow codebase pipelines to codestar-connections:GetConnectionToken ([#579](https://github.com/uktrade/platform-tools/issues/579)) ([bef6864](https://github.com/uktrade/platform-tools/commit/bef6864a1ca1dea13532a85fd4142f59a4538546))

## [10.11.0](https://github.com/uktrade/platform-tools/compare/10.10.0...10.11.0) (2024-09-23)


### Features

* **copilot-bootstrap:** enable pingdom health checks ([#573](https://github.com/uktrade/platform-tools/issues/573)) ([e063c3b](https://github.com/uktrade/platform-tools/commit/e063c3b52bc89a8fead1b44922dc4b97ba0c8bbb))
* dbtp 1202 add cdn ([#562](https://github.com/uktrade/platform-tools/issues/562)) ([b825bdf](https://github.com/uktrade/platform-tools/commit/b825bdfa065e8b302bcefa37cffb4ccb42d40cce))
* **nginx-proxy:** support proxying websocket connections ([#571](https://github.com/uktrade/platform-tools/issues/571)) ([40fbc65](https://github.com/uktrade/platform-tools/commit/40fbc6563178591c7f51a9ed45829c027a91b957))


### Bug Fixes

* Add source ip rule to maintenance pages ([#574](https://github.com/uktrade/platform-tools/issues/574)) ([1e6aa29](https://github.com/uktrade/platform-tools/commit/1e6aa291d85cda78bb592341a66eb66c8d8ea6b0))
* Addressing workflow bug in DBTP-1083 ([#577](https://github.com/uktrade/platform-tools/issues/577)) ([2fb1705](https://github.com/uktrade/platform-tools/commit/2fb1705e453ed017a4642192f0ee0ca36f9a8f65))
* DBTP-1282 allow for explicit settings of PUB_PATH_LIST ([#561](https://github.com/uktrade/platform-tools/issues/561)) ([2c41170](https://github.com/uktrade/platform-tools/commit/2c4117099fa5e48cc2b94ad7daf5e8c04bff8138))
* ensure delete_listener_rule deletes multiple rules with same name ([#578](https://github.com/uktrade/platform-tools/issues/578)) ([8b2665d](https://github.com/uktrade/platform-tools/commit/8b2665d124f1a9ad560caf89666a131540027932))
* ensure online command removes all rule types ([#576](https://github.com/uktrade/platform-tools/issues/576)) ([f36f22a](https://github.com/uktrade/platform-tools/commit/f36f22a7b21a229a9ddbe03bc52dd9f043493e62))
* Small fix that allows you to generate environment config without chan… ([#568](https://github.com/uktrade/platform-tools/issues/568)) ([8133855](https://github.com/uktrade/platform-tools/commit/813385597729dd2ed35e449f3e83a05986214c19))

## [10.10.0](https://github.com/uktrade/platform-tools/compare/10.9.1...10.10.0) (2024-09-12)


### Features

* DBTP 1162 support hosting static sites on s3 ([#555](https://github.com/uktrade/platform-tools/issues/555)) ([4e47ea0](https://github.com/uktrade/platform-tools/commit/4e47ea0697e49e7b43467fbeca48af2995bd6ccf))

## [10.9.1](https://github.com/uktrade/platform-tools/compare/10.9.0...10.9.1) (2024-09-11)


### Bug Fixes

* DBTP-1331 Ensure environment generate retrieves correct certificate for load balancer ([#556](https://github.com/uktrade/platform-tools/issues/556)) ([0830410](https://github.com/uktrade/platform-tools/commit/0830410581b66f032c3f95a796ddb089f8454823))

## [10.9.0](https://github.com/uktrade/platform-tools/compare/10.8.1...10.9.0) (2024-09-10)


### Features

* DBTP-1301 - provide cross account s3 to s3 data migration permissions ([#540](https://github.com/uktrade/platform-tools/issues/540)) ([8e9cea5](https://github.com/uktrade/platform-tools/commit/8e9cea5a48f6f8cf04a4c845d7bf85873126eb60))

## [10.8.1](https://github.com/uktrade/platform-tools/compare/10.8.0...10.8.1) (2024-09-05)


### Bug Fixes

* add medium-ha postgres plan ([#551](https://github.com/uktrade/platform-tools/issues/551)) ([72bb681](https://github.com/uktrade/platform-tools/commit/72bb6816ce0ab196f19b6e386cab3f0c931bbc2d))

## [10.8.0](https://github.com/uktrade/platform-tools/compare/10.7.4...10.8.0) (2024-09-05)


### Features

* DBTP-1001 Add optional deploy_repository_branch to the codebase pipeline config ([#545](https://github.com/uktrade/platform-tools/issues/545)) ([e5c5235](https://github.com/uktrade/platform-tools/commit/e5c5235fafadab89e886084e867c8aa7c98c2945))
* DBTP-1346 Add special characters & urlencode password parameters to OpenSearch validation ([#549](https://github.com/uktrade/platform-tools/issues/549)) ([1b069af](https://github.com/uktrade/platform-tools/commit/1b069affc93551f0b716757346fddfca7bc7ab05))

## [10.7.4](https://github.com/uktrade/platform-tools/compare/10.7.3...10.7.4) (2024-08-29)


### Bug Fixes

* Use tag-latest for ci-image-builder ([#543](https://github.com/uktrade/platform-tools/issues/543)) ([a4340de](https://github.com/uktrade/platform-tools/commit/a4340dec73b6800fafcf19fb32824561e1b757b9))

## [10.7.3](https://github.com/uktrade/platform-tools/compare/10.7.2...10.7.3) (2024-08-28)


### Bug Fixes

* DBTP-1323 Broken `platform-helper codebase \*` commands ([#542](https://github.com/uktrade/platform-tools/issues/542)) ([fd0e185](https://github.com/uktrade/platform-tools/commit/fd0e1857f4343e42ab260a10858e7a343cc95551))
* S3 bucket KMS Key lookup when environments are in multiple AWS ac… ([#536](https://github.com/uktrade/platform-tools/issues/536)) ([960557d](https://github.com/uktrade/platform-tools/commit/960557debe894d9dad78ffd83caf43086065d48e))

## [10.7.2](https://github.com/uktrade/platform-tools/compare/10.7.1...10.7.2) (2024-08-22)


### Bug Fixes

* Replace .platform-helper-version check in buildspec ([#538](https://github.com/uktrade/platform-tools/issues/538)) ([6764c6c](https://github.com/uktrade/platform-tools/commit/6764c6c2a8412aff8fe3573e7eebed61a0fbd977))

## [10.7.1](https://github.com/uktrade/platform-tools/compare/10.7.0...10.7.1) (2024-08-19)


### Bug Fixes

* DBTP-1294 Allow any environment deployment by deploy codebuild job ([#528](https://github.com/uktrade/platform-tools/issues/528)) ([3fad07a](https://github.com/uktrade/platform-tools/commit/3fad07aabe8e7cc75e2003f6dc1cd606f45c19c8))

## [10.7.0](https://github.com/uktrade/platform-tools/compare/10.6.1...10.7.0) (2024-08-19)


### Features

* Allow override of platform-helper version in regression pipeline ([#527](https://github.com/uktrade/platform-tools/issues/527)) ([5241adf](https://github.com/uktrade/platform-tools/commit/5241adf72108054dd7d17278ec1c5828c6be1358))


### Bug Fixes

* add a policy to allow services to access global SSM parameters ([#531](https://github.com/uktrade/platform-tools/issues/531)) ([6fb9795](https://github.com/uktrade/platform-tools/commit/6fb9795cbf56963af8483ec018c16771f351390a))

## [10.6.1](https://github.com/uktrade/platform-tools/compare/10.6.0...10.6.1) (2024-08-12)


### Bug Fixes

* Add target environment override to smoke tests ([#524](https://github.com/uktrade/platform-tools/issues/524)) ([5edc1c2](https://github.com/uktrade/platform-tools/commit/5edc1c29204567f60cedbf30670ef763a2470753))
* DBTP-1180 - list all latest images tagged as commits ([#529](https://github.com/uktrade/platform-tools/issues/529)) ([12c3d5d](https://github.com/uktrade/platform-tools/commit/12c3d5d97dacd09b75c58a3d50e4808ae632c83b))
* DBTP-1207 - align extensions module name ([#530](https://github.com/uktrade/platform-tools/issues/530)) ([3511c42](https://github.com/uktrade/platform-tools/commit/3511c424e8cc47e69aee05276f873dff02f6e6f4))

## [10.6.0](https://github.com/uktrade/platform-tools/compare/10.5.0...10.6.0) (2024-08-02)


### Features

* DBTP-1151 Add submodules script to pre_build.sh template ([#516](https://github.com/uktrade/platform-tools/issues/516)) ([e7ae76a](https://github.com/uktrade/platform-tools/commit/e7ae76abe6cbdf1682c6abb45128bdbf84d566a1))
* DBTP-1154 add the prometheus prod service policy by default ([#509](https://github.com/uktrade/platform-tools/issues/509)) ([35f52f7](https://github.com/uktrade/platform-tools/commit/35f52f71338d76071448c7294938616159390212))


### Bug Fixes

* correct conduit log group name ([#523](https://github.com/uktrade/platform-tools/issues/523)) ([acd233c](https://github.com/uktrade/platform-tools/commit/acd233cacba88fa01b28ba11d9166fbce8f1a718))
* DBTP-1236 - Fix codebase deploy to multiple environments ([#517](https://github.com/uktrade/platform-tools/issues/517)) ([be3ba7c](https://github.com/uktrade/platform-tools/commit/be3ba7c6fc287257846d332dba03c0257d32af76))
* DBTP-1265 fix platform helper version file missing ([#521](https://github.com/uktrade/platform-tools/issues/521)) ([04adf14](https://github.com/uktrade/platform-tools/commit/04adf146673759cc68b943a8827ff4d53eb8aaa6))

## [10.5.0](https://github.com/uktrade/platform-tools/compare/10.4.0...10.5.0) (2024-07-30)


### Features

* Add ability to override the terraform-platform-modules version in the platform-config.yml file. ([#504](https://github.com/uktrade/platform-tools/issues/504)) ([4dbb314](https://github.com/uktrade/platform-tools/commit/4dbb314e5156e451630b0336c4ef9ee08a292449))
* DBTP-1137 Add parameter to environment pipeline to allow triggering of other pipeline ([#515](https://github.com/uktrade/platform-tools/issues/515)) ([832b463](https://github.com/uktrade/platform-tools/commit/832b463fcfb6607cf1477111da767a4eba9f3052))


### Bug Fixes

* Add trailing new lines to some auto generated files ([#512](https://github.com/uktrade/platform-tools/issues/512)) ([d5454ca](https://github.com/uktrade/platform-tools/commit/d5454ca0a2e011adcc80b98f088b31c8db11894a))
* DBTP-1044 as a developer when i enable a maintenance page i should still be able to access the service (PT. 2) ([#473](https://github.com/uktrade/platform-tools/issues/473)) ([8ce58b3](https://github.com/uktrade/platform-tools/commit/8ce58b3152e5c79cdbfa74a0f4c67e1e6fc856b8))
* DBTP-1152 - slack notifications work when GitHub-Hookshot triggers build ([#501](https://github.com/uktrade/platform-tools/issues/501)) ([71c1c20](https://github.com/uktrade/platform-tools/commit/71c1c20ad73ece2fd34945a5beb458b3eb8251fc))


### Documentation

* Correct introductory paragraph on the Platform Helper README.md ([#513](https://github.com/uktrade/platform-tools/issues/513)) ([20285ac](https://github.com/uktrade/platform-tools/commit/20285ac5f48de68f0b76f6b4d60b9e12b482d451))
* Update regression tests documentation ([#507](https://github.com/uktrade/platform-tools/issues/507)) ([5746e3a](https://github.com/uktrade/platform-tools/commit/5746e3a1b8eab160162ad693ae831f4e0ede7dd6))

## [10.4.0](https://github.com/uktrade/platform-tools/compare/10.3.0...10.4.0) (2024-07-16)


### Features

* DBTP-1109 - Add command to copy data ([#488](https://github.com/uktrade/platform-tools/issues/488)) ([825a68b](https://github.com/uktrade/platform-tools/commit/825a68bd7b3f6526abae4423108cfdb67f01f5c2))
* DBTP-1133 Add option to specify terraform-platform-modules version on the platform-helper environment generate command ([#503](https://github.com/uktrade/platform-tools/issues/503)) ([521a1fb](https://github.com/uktrade/platform-tools/commit/521a1fbe3699a9ee48f0f70b0eb7436478c01b31))


### Bug Fixes

* DBPT-1128 Connection Error when connecting to Redis via Conduit ([#498](https://github.com/uktrade/platform-tools/issues/498)) ([330cc14](https://github.com/uktrade/platform-tools/commit/330cc14d161fff1441d4b1c89bfc6442c81fc7cf))
* test_validation.py::test_validate_success runs against all resources in the fixture ([#493](https://github.com/uktrade/platform-tools/issues/493)) ([1206b78](https://github.com/uktrade/platform-tools/commit/1206b7872e4534a75d3eaed3d08335d29d9f9465))

## [10.3.0](https://github.com/uktrade/platform-tools/compare/10.2.0...10.3.0) (2024-07-10)


### Features

* Added an 'account' parameter to the environment_pipelines config ([#490](https://github.com/uktrade/platform-tools/issues/490)) ([b0ad4d1](https://github.com/uktrade/platform-tools/commit/b0ad4d19b529aa14abf0861da5e1572364f8164c))


### Bug Fixes

* Dbtp-1094 use platform-helper notify for Slack alert on publish to PyPi ([#494](https://github.com/uktrade/platform-tools/issues/494)) ([dcb3482](https://github.com/uktrade/platform-tools/commit/dcb3482d3b8cf5838bd595e27ebf341f5c04a201))
* DBTP-1148 platform-helper environment generate should exit it not logged in ([#496](https://github.com/uktrade/platform-tools/issues/496)) ([4ae5e7b](https://github.com/uktrade/platform-tools/commit/4ae5e7bb415cf59a35da1d5aed7d9213c38468e3))

## [10.2.0](https://github.com/uktrade/platform-tools/compare/10.1.0...10.2.0) (2024-07-05)


### Features

* DBTP-1116 - Support configuration of the RDS backup retention period ([#491](https://github.com/uktrade/platform-tools/issues/491)) ([a431184](https://github.com/uktrade/platform-tools/commit/a431184fda45183f9ed287d2b9e685b86420d992))

## [10.1.0](https://github.com/uktrade/platform-tools/compare/10.0.0...10.1.0) (2024-07-04)


### Features

* Add defaults to AWS config ([#487](https://github.com/uktrade/platform-tools/issues/487)) ([ae66e93](https://github.com/uktrade/platform-tools/commit/ae66e9347c542cee77d933d9a80e89dbf529b8fe))
* DBTP-1040 - add support for s3 lifecycle policies ([#485](https://github.com/uktrade/platform-tools/issues/485)) ([92c7dc8](https://github.com/uktrade/platform-tools/commit/92c7dc8649f7c3514ce3066e3c04488eaad0619e))

## [10.0.0](https://github.com/uktrade/platform-tools/compare/9.0.1...10.0.0) (2024-07-01)


### ⚠ BREAKING CHANGES

* Update to use terraform-platform-modules 4 ([#482](https://github.com/uktrade/platform-tools/issues/482))

### Features

* Update to use terraform-platform-modules 4 ([#482](https://github.com/uktrade/platform-tools/issues/482)) ([1d91bc5](https://github.com/uktrade/platform-tools/commit/1d91bc5b54322141c1a3ee5db1bacb6b0e5f358b))

## [9.0.1](https://github.com/uktrade/platform-tools/compare/9.0.0...9.0.1) (2024-06-28)


### Bug Fixes

* DBTP-1093 - Add postgres version 16 to conduit image ([#477](https://github.com/uktrade/platform-tools/issues/477)) ([7d8747a](https://github.com/uktrade/platform-tools/commit/7d8747a2e4c39b8417d1c2b7a12d0ca56761d8e0))
* DBTP-1504 - Fix unauthorised error in OpenSearch conduit CLI ([#483](https://github.com/uktrade/platform-tools/issues/483)) ([1248ddd](https://github.com/uktrade/platform-tools/commit/1248dddb942702930aaed8ae055839dd86a076e8))

## [9.0.0](https://github.com/uktrade/platform-tools/compare/8.8.0...9.0.0) (2024-06-21)


### ⚠ BREAKING CHANGES

* Changed platform-helper to use the combined platform-config.yml file rather than individual config files. ([#461](https://github.com/uktrade/platform-tools/issues/461))

### Features

* Changed platform-helper to use the combined platform-config.yml file rather than individual config files. ([#461](https://github.com/uktrade/platform-tools/issues/461)) ([b9bbef2](https://github.com/uktrade/platform-tools/commit/b9bbef2574fa0c4da0d416d6d8d84ba985f97d41))


### Bug Fixes

* **pipeline:** codebase pipelines branch name may be undefined error ([#474](https://github.com/uktrade/platform-tools/issues/474)) ([41de810](https://github.com/uktrade/platform-tools/commit/41de810a21968b4ae3a847ebdce503477238f5c4))

## [8.8.0](https://github.com/uktrade/platform-tools/compare/8.7.0...8.8.0) (2024-06-17)


### Features

* support developers bypassing maintenance pages ([#453](https://github.com/uktrade/platform-tools/issues/453)) ([8cba322](https://github.com/uktrade/platform-tools/commit/8cba3228283ef11ea7361acc1335321996a56fef))

## [8.7.0](https://github.com/uktrade/platform-tools/compare/8.6.0...8.7.0) (2024-06-17)


### Features

* DBTP-612 allow wildcard in branch names ([#457](https://github.com/uktrade/platform-tools/issues/457)) ([9b9aaf2](https://github.com/uktrade/platform-tools/commit/9b9aaf2fa3832ddbb9ec3a972501d0286cdcfba9))


### Bug Fixes

* add dmas-migration to available environment template options ([#468](https://github.com/uktrade/platform-tools/issues/468)) ([6e98ca1](https://github.com/uktrade/platform-tools/commit/6e98ca13bde76612ead0622cd56fee9490dc3e41))


### Documentation

* Fix typo in README ([#464](https://github.com/uktrade/platform-tools/issues/464)) ([3ce139f](https://github.com/uktrade/platform-tools/commit/3ce139f4c643821928c4ac248f366d45de243f39))

## [8.6.0](https://github.com/uktrade/platform-tools/compare/8.5.0...8.6.0) (2024-06-10)


### Features

* Add prometheus-policy extension type ([#456](https://github.com/uktrade/platform-tools/issues/456)) ([e2b37ab](https://github.com/uktrade/platform-tools/commit/e2b37ab251a86d7ef65b276434522589bec078ed))


### Bug Fixes

* DBTP-1053 - Fix opensearch conduit parameter path ([#458](https://github.com/uktrade/platform-tools/issues/458)) ([b7e7b07](https://github.com/uktrade/platform-tools/commit/b7e7b0776f72300384a952a6daae54b95415718a))

## [8.5.0](https://github.com/uktrade/platform-tools/compare/8.4.1...8.5.0) (2024-05-31)


### Features

* Add slack notification commands ([#448](https://github.com/uktrade/platform-tools/issues/448)) ([ddd33fb](https://github.com/uktrade/platform-tools/commit/ddd33fb11bdb932f306c3d0443ad8b3504918146))


### Bug Fixes

* redis and opensearch parameters missing ENDPOINT suffix ([#446](https://github.com/uktrade/platform-tools/issues/446)) ([99f1c3f](https://github.com/uktrade/platform-tools/commit/99f1c3f2a3a396585580e115172ac262a8d4ff61))

## [8.4.1](https://github.com/uktrade/platform-tools/compare/8.4.0...8.4.1) (2024-05-23)


### Bug Fixes

* platform-helper generate ALB bugfixes ([#438](https://github.com/uktrade/platform-tools/issues/438)) ([3ba7471](https://github.com/uktrade/platform-tools/commit/3ba747110ec080d736344d279b3130b6fba08ec4))

## [8.4.0](https://github.com/uktrade/platform-tools/compare/8.3.0...8.4.0) (2024-05-22)


### Features

* Cleaning out pipelines config before regenerating ([#439](https://github.com/uktrade/platform-tools/issues/439)) ([421b8f9](https://github.com/uktrade/platform-tools/commit/421b8f9ceb22ee11d455d580589f08b67276c175))


### Bug Fixes

* DBTP-909 - Remove CloudWatch log resource policy ([#440](https://github.com/uktrade/platform-tools/issues/440)) ([0a3e167](https://github.com/uktrade/platform-tools/commit/0a3e167b79a243eeeb5a81a0bdc5d9d5129fd4c4))
* Update get_s3_kms_alias_arns to check for environment name ([#442](https://github.com/uktrade/platform-tools/issues/442)) ([36e41e6](https://github.com/uktrade/platform-tools/commit/36e41e64293618ce0816a459a6fd7fa408abc3a9))

## [8.3.0](https://github.com/uktrade/platform-tools/compare/8.2.1...8.3.0) (2024-05-20)


### Features

* DBTP-933 Add option to Platform-helper to manage .aws/config file ([#428](https://github.com/uktrade/platform-tools/issues/428)) ([9b8e0a3](https://github.com/uktrade/platform-tools/commit/9b8e0a3356afb3b2deed7b490ce607ca2606341b))
* DBTP-969 Allow HTTPS GitHub clones ([#432](https://github.com/uktrade/platform-tools/issues/432)) ([0b1085d](https://github.com/uktrade/platform-tools/commit/0b1085d92c859493b3a0e3ecc722282245c35e84))
* Validation usability improvements ([#430](https://github.com/uktrade/platform-tools/issues/430)) ([ee80ed0](https://github.com/uktrade/platform-tools/commit/ee80ed04f3048b54d83da99ee35e5364cb07ff25))


### Bug Fixes

* DBTP-989 Make platform-helper generate skip generating AWS Copilot environment pipelines for Terraformed applications ([#431](https://github.com/uktrade/platform-tools/issues/431)) ([04b5092](https://github.com/uktrade/platform-tools/commit/04b509265ed5c4246e3fde15f1898f9c06ca528d))


### Documentation

* Mention releasing non-breaking changes before merging breaking changes ([#437](https://github.com/uktrade/platform-tools/issues/437)) ([bee47b6](https://github.com/uktrade/platform-tools/commit/bee47b6a4851e404faf170feb007a10b75b1bdb7))

## [8.2.1](https://github.com/uktrade/platform-tools/compare/8.2.0...8.2.1) (2024-05-07)


### Bug Fixes

* env generate vpc name not found bug ([#426](https://github.com/uktrade/platform-tools/issues/426)) ([2acf0fc](https://github.com/uktrade/platform-tools/commit/2acf0fcb1e3169dccf91254c83b5089b40860163))

## [8.2.0](https://github.com/uktrade/platform-tools/compare/8.1.0...8.2.0) (2024-05-03)


### Features

* DBTP-860 Add a command to generate/update environment manifest files with VPC/ALB config ([#412](https://github.com/uktrade/platform-tools/issues/412)) ([27f5f1f](https://github.com/uktrade/platform-tools/commit/27f5f1f8a9e5cf7e7a3b9e7ae50ca7b583c273d1))

## [8.1.0](https://github.com/uktrade/platform-tools/compare/8.0.0...8.1.0) (2024-05-02)


### Features

* DBTP-779 - Trigger documentation update on new release ([#417](https://github.com/uktrade/platform-tools/issues/417)) ([22bb105](https://github.com/uktrade/platform-tools/commit/22bb10532e56b073fb13873373ffa80a69fa8988))


### Bug Fixes

* DBTP-953 Unable to set up conduit with admin user ([#423](https://github.com/uktrade/platform-tools/issues/423)) ([1c86195](https://github.com/uktrade/platform-tools/commit/1c86195d359c3f7c3d5b83bb9c586b81d9a6f176))
* update Postgres addon type for Conduit ([#422](https://github.com/uktrade/platform-tools/issues/422)) ([2b43960](https://github.com/uktrade/platform-tools/commit/2b43960ac64d04ec8595916f7f6fe92fd97794d2))
* Use fake file system for create command docs happy path test ([#414](https://github.com/uktrade/platform-tools/issues/414)) ([bcb9878](https://github.com/uktrade/platform-tools/commit/bcb98782fcbcee7b41cf735aaecc7a235875e3dc))

## [8.0.0](https://github.com/uktrade/platform-tools/compare/7.0.0...8.0.0) (2024-04-24)


### ⚠ BREAKING CHANGES

* DBTP-885 Rename addons.yml to extensions.yml ([#413](https://github.com/uktrade/platform-tools/issues/413))
* DBTP-905 Remove unused bootstrap config files ([#406](https://github.com/uktrade/platform-tools/issues/406))
* Update aws-cdk and aws-cdk-packages to fix CVE 5777 ([#409](https://github.com/uktrade/platform-tools/issues/409))
* DBTP-905 Remove bootstrap commands and requirement for bootstrap.yml ([#402](https://github.com/uktrade/platform-tools/issues/402))

### Features

* set the ECS cluster name ([#407](https://github.com/uktrade/platform-tools/issues/407)) ([8f6af32](https://github.com/uktrade/platform-tools/commit/8f6af32532e112a0bd550884acee98bc0ca1f654))


### Bug Fixes

* DBTP-907 Platform helper generate version file ([#403](https://github.com/uktrade/platform-tools/issues/403)) ([f386383](https://github.com/uktrade/platform-tools/commit/f386383fc511757bdf9231f0ffe3a1d8aa971461))
* DPTP-923 Mock function that causes problems in generate tests ([#411](https://github.com/uktrade/platform-tools/issues/411)) ([3eb57bf](https://github.com/uktrade/platform-tools/commit/3eb57bf35301a489bc520aad4b3c2c95ee0fd6d6))
* Update aws-cdk and aws-cdk-packages to fix CVE 5777 ([#409](https://github.com/uktrade/platform-tools/issues/409)) ([ed3fe10](https://github.com/uktrade/platform-tools/commit/ed3fe1063b3851f2b5b568976bc79a5da2f9b5f5))


### Miscellaneous Chores

* DBTP-885 Rename addons.yml to extensions.yml ([#413](https://github.com/uktrade/platform-tools/issues/413)) ([ecdabd7](https://github.com/uktrade/platform-tools/commit/ecdabd7cca94bd7cb4d55c866327734c22f81fb0))
* DBTP-905 Remove bootstrap commands and requirement for bootstrap.yml ([#402](https://github.com/uktrade/platform-tools/issues/402)) ([08019eb](https://github.com/uktrade/platform-tools/commit/08019eba2cf909e4ea3bae008f13ca8ee8dd3d72))
* DBTP-905 Remove unused bootstrap config files ([#406](https://github.com/uktrade/platform-tools/issues/406)) ([70e9aec](https://github.com/uktrade/platform-tools/commit/70e9aecc836094e07fc234faf9cbc7606b76ff37))

## [7.0.0](https://github.com/uktrade/platform-tools/compare/6.2.1...7.0.0) (2024-04-15)


### ⚠ BREAKING CHANGES

* DBTP-859 Modify make-addons to support Terraform stack ([#391](https://github.com/uktrade/platform-tools/issues/391))

### Features

* DBTP-777 - Automate release version ([#395](https://github.com/uktrade/platform-tools/issues/395)) ([ce28788](https://github.com/uktrade/platform-tools/commit/ce287883bde04fab01062fb330ec76229fb2ff2a))
* DBTP-859 Modify make-addons to support Terraform stack ([#391](https://github.com/uktrade/platform-tools/issues/391)) ([b3eb9db](https://github.com/uktrade/platform-tools/commit/b3eb9db2976fe337b690649b66e939336d1ccc6c))
