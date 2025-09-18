# Changelog

## [15.9.0](https://github.com/uktrade/platform-tools/compare/15.8.0...15.9.0) (2025-09-09)


### Features

* Apply ecs-service terraform in codebase pipelines (DBTP-2160) ([#970](https://github.com/uktrade/platform-tools/issues/970)) ([175c899](https://github.com/uktrade/platform-tools/commit/175c899044e5dbecbe3365d5516085c16298d676))
* Configure default providers for pipeline terraform to allow apply only with relevant profile and account_ids (DBPT-2031) ([#982](https://github.com/uktrade/platform-tools/issues/982)) ([bbc7f58](https://github.com/uktrade/platform-tools/commit/bbc7f58f3f97ec426e889f1976a584f0251b3945))
* Convert copilot overrides (DBTP-2231) ([#993](https://github.com/uktrade/platform-tools/issues/993)) ([a53ba2f](https://github.com/uktrade/platform-tools/commit/a53ba2f327259e7f7f0bf6293288b37de3abfb3f))
* Replace copilot service addons (DBTP-2230) ([#994](https://github.com/uktrade/platform-tools/issues/994)) ([f695c26](https://github.com/uktrade/platform-tools/commit/f695c26641dd80fefdb4275dde0d3868dc26e509))
* Service config migration (DBTP-2195) ([#916](https://github.com/uktrade/platform-tools/issues/916)) ([a9fdacb](https://github.com/uktrade/platform-tools/commit/a9fdacb5ddb7b95aa788ea82790fe4886bf7d1d0))


### Bug Fixes

* Add additional tags to maintenance page rules (DBTP-2281) ([#1034](https://github.com/uktrade/platform-tools/issues/1034)) ([90b177d](https://github.com/uktrade/platform-tools/commit/90b177d921880005b32b018325c1c361227cf78b))
* False success from pipeline after failed deployment (DBTP-2311) ([#1033](https://github.com/uktrade/platform-tools/issues/1033)) ([2f1ba5e](https://github.com/uktrade/platform-tools/commit/2f1ba5e2b3372a423bc1fd66154480e5209f56d8))
* Make service terraform pipeline stage conditional (off-ticket) ([#1020](https://github.com/uktrade/platform-tools/issues/1020)) ([c3c8c17](https://github.com/uktrade/platform-tools/commit/c3c8c17810436a3eb67143281980e5c8b3d4aa9f))
* Update Terraform AWS provider version (DBTP-2263) ([#1015](https://github.com/uktrade/platform-tools/issues/1015)) ([9f72fcc](https://github.com/uktrade/platform-tools/commit/9f72fcce2cb70eefa0224ece5840d9bc2e221585))
* Update terraform versions (DBTP-1704) ([#991](https://github.com/uktrade/platform-tools/issues/991)) ([b7f52da](https://github.com/uktrade/platform-tools/commit/b7f52daf06138fd88161adfd86ce9def0c88e3ea))


### Dependencies

* Bump checkov from 3.2.458 to 3.2.461 ([#988](https://github.com/uktrade/platform-tools/issues/988)) ([7a978ea](https://github.com/uktrade/platform-tools/commit/7a978ea041d9a2aeed5601e16c4eaf63538ecd6b))
* Bump jsonschema from 4.17.3 to 4.25.1 ([#995](https://github.com/uktrade/platform-tools/issues/995)) ([a1c9d34](https://github.com/uktrade/platform-tools/commit/a1c9d34f87cd41a9e83f48f25ee2f076e3ff7e86))
* Bump yamllint from 1.35.1 to 1.37.1 ([#1016](https://github.com/uktrade/platform-tools/issues/1016)) ([52e2626](https://github.com/uktrade/platform-tools/commit/52e2626cba11199f1dc52ce3c3458228c62b7f40))

## [15.8.0](https://github.com/uktrade/platform-tools/compare/15.7.0...15.8.0) (2025-08-13)


### Features

* Constrain environment terraform to only apply in the relevant aws account ID (DBTP-2031) ([#977](https://github.com/uktrade/platform-tools/issues/977)) ([f29e37e](https://github.com/uktrade/platform-tools/commit/f29e37e04f695f18b5f59cc7aaf225962506ef56))
* Various updates and enhancements to Datadog service metadata (DBTP-2244) ([#969](https://github.com/uktrade/platform-tools/issues/969)) ([2e45b38](https://github.com/uktrade/platform-tools/commit/2e45b38e7359f0f0667ee7f3d97b9f2b230c470d))


### Bug Fixes

* Allow multiple destination environments for a database copy pipeline (off-ticket) ([#971](https://github.com/uktrade/platform-tools/issues/971)) ([0ae916f](https://github.com/uktrade/platform-tools/commit/0ae916fa5a76b6154abb6978e80d721dd75fd3c3))
* Reduce addons parameter size (DBTP-2272) ([#987](https://github.com/uktrade/platform-tools/issues/987)) ([f60d949](https://github.com/uktrade/platform-tools/commit/f60d949a03a3de1e92e046a39990e14b0a9532a7))
* Remove obsolete SSM param (DBTP-2264) ([#986](https://github.com/uktrade/platform-tools/issues/986)) ([e026763](https://github.com/uktrade/platform-tools/commit/e02676377b5972f0f12827ba4964c1411f323d87))


### Dependencies

* Bump checkov from 3.2.453 to 3.2.457 ([#964](https://github.com/uktrade/platform-tools/issues/964)) ([c5881d8](https://github.com/uktrade/platform-tools/commit/c5881d8b86144469b7ef025fdf296eefc9416e18))
* Bump checkov from 3.2.457 to 3.2.458 ([#975](https://github.com/uktrade/platform-tools/issues/975)) ([0b64188](https://github.com/uktrade/platform-tools/commit/0b641886ad4babb163f71ee25c103ab301dfd427))
* Bump mypy-boto3-codebuild from 1.37.29 to 1.40.0 ([#968](https://github.com/uktrade/platform-tools/issues/968)) ([8e7b2ad](https://github.com/uktrade/platform-tools/commit/8e7b2ada2e8bbb12d3bed8a9c24d8b954bdb4017))

## [15.7.0](https://github.com/uktrade/platform-tools/compare/15.6.0...15.7.0) (2025-08-04)


### Features

* Cache invalidations in the codebase pipelines (DBTP-2105) ([#891](https://github.com/uktrade/platform-tools/issues/891)) ([12be322](https://github.com/uktrade/platform-tools/commit/12be322a3b8b77a68edcfb9c150293cd1ec09c19))
* Service generate command (DBTP-2155) ([#915](https://github.com/uktrade/platform-tools/issues/915)) ([ecf20d5](https://github.com/uktrade/platform-tools/commit/ecf20d57e3cd495290e5c8c348bbd095af43fe81))
* Terraform resources for ECS service (DBTP-2154) ([#909](https://github.com/uktrade/platform-tools/issues/909)) ([e47fbdf](https://github.com/uktrade/platform-tools/commit/e47fbdfc44844aa7984bff8fc1445a602375efd9))


### Bug Fixes

* Give permission for DataDog process level resource monitoring (DBTP-2238) ([#918](https://github.com/uktrade/platform-tools/issues/918)) ([23b750a](https://github.com/uktrade/platform-tools/commit/23b750ab2d61b416726a9b9e10918982a3c1a437))


### Dependencies

* Bump aiohttp from 3.11.16 to 3.12.14 ([#923](https://github.com/uktrade/platform-tools/issues/923)) ([0e6717a](https://github.com/uktrade/platform-tools/commit/0e6717a9cdbde09f5fb81a64f15c7f19f1a870fc))
* Bump cfn-lint from 1.33.2 to 1.38.0 ([#927](https://github.com/uktrade/platform-tools/issues/927)) ([c9e6b91](https://github.com/uktrade/platform-tools/commit/c9e6b919e8624b0b5f6a5e5ca347dc56bd5a4f34))
* Bump checkov from 3.2.405 to 3.2.453 ([#926](https://github.com/uktrade/platform-tools/issues/926)) ([1c6b220](https://github.com/uktrade/platform-tools/commit/1c6b2206d5a636cccd433bc5f3b8532ceb86226b))
* Bump protobuf from 4.25.5 to 4.25.8 ([#935](https://github.com/uktrade/platform-tools/issues/935)) ([4d985d3](https://github.com/uktrade/platform-tools/commit/4d985d37c54da5d79d7c952010625173f2fd1a6c))
* Bump pycares from 4.6.0 to 4.9.0 ([#922](https://github.com/uktrade/platform-tools/issues/922)) ([cd38f84](https://github.com/uktrade/platform-tools/commit/cd38f846a0aa618eabf589c4c189682f81b84a0e))
* Bump pyyaml from 6.0.1 to 6.0.2 ([#932](https://github.com/uktrade/platform-tools/issues/932)) ([bb285e1](https://github.com/uktrade/platform-tools/commit/bb285e18fbddb8516984152ea3cc70c9e7627860))
* Bump requests from 2.32.3 to 2.32.4 ([#924](https://github.com/uktrade/platform-tools/issues/924)) ([2e3cafb](https://github.com/uktrade/platform-tools/commit/2e3cafbb8918820604e1be4c7becbd8566b6f935))
* Bump semver from 3.0.2 to 3.0.4 ([#965](https://github.com/uktrade/platform-tools/issues/965)) ([de9c169](https://github.com/uktrade/platform-tools/commit/de9c169541a021f439fd48e0657f1ed23d578a61))
* Bump tomlkit from 0.12.5 to 0.13.3 ([#928](https://github.com/uktrade/platform-tools/issues/928)) ([7326bbc](https://github.com/uktrade/platform-tools/commit/7326bbcbaef83c7ca0db71110b19097324cb3391))

## [15.6.0](https://github.com/uktrade/platform-tools/compare/15.5.0...15.6.0) (2025-07-15)


### Features

* Add link to standard dashboard to each service (DBTP-2193) ([#912](https://github.com/uktrade/platform-tools/issues/912)) ([9215103](https://github.com/uktrade/platform-tools/commit/921510328b6cd4b4087e5a7feb395dac5fac47fa))
* Conduit and data copy new sg (DBPT-2074) ([#908](https://github.com/uktrade/platform-tools/issues/908)) ([d9234ae](https://github.com/uktrade/platform-tools/commit/d9234ae6472314009981a97f1c252338321f1d0f))


### Bug Fixes

* Add CreateCluster permission (off-ticket) ([#913](https://github.com/uktrade/platform-tools/issues/913)) ([52c705d](https://github.com/uktrade/platform-tools/commit/52c705d6137e270342fa381b4a1bccd7e80addc8))
* Handle missing ssm permission when getting environment details (off-ticket) ([#914](https://github.com/uktrade/platform-tools/issues/914)) ([c503c7d](https://github.com/uktrade/platform-tools/commit/c503c7d58cda0c1e5ed2fa50c85861afba2f1325))
* Update db clear script (off-ticket) ([#910](https://github.com/uktrade/platform-tools/issues/910)) ([9d66a44](https://github.com/uktrade/platform-tools/commit/9d66a44023d2cbe3621f5023fee76529d2886e23))

## [15.5.0](https://github.com/uktrade/platform-tools/compare/15.4.2...15.5.0) (2025-07-08)


### Features

* Create Terraform ECS cluster (DBTP-2153) ([#905](https://github.com/uktrade/platform-tools/issues/905)) ([4e29864](https://github.com/uktrade/platform-tools/commit/4e298642628d6f92f84a1e59d60f62903649dbc7))
* Update platform schema to include service deployment mode (DBTP-2152) ([#906](https://github.com/uktrade/platform-tools/issues/906)) ([c7b3cf9](https://github.com/uktrade/platform-tools/commit/c7b3cf9436e8b5edadbdaf59e064ae79b5e57242))


### Bug Fixes

* Add default value for service-deployment-mode (DBTP-2153) ([#907](https://github.com/uktrade/platform-tools/issues/907)) ([8f8a360](https://github.com/uktrade/platform-tools/commit/8f8a360baea0805f2a582b247c586d9143590fb3))
* Conduit missing SSM parameters bug (DBTP-2112) ([#902](https://github.com/uktrade/platform-tools/issues/902)) ([74bb3d1](https://github.com/uktrade/platform-tools/commit/74bb3d12426b6c0860f152b609fdf78d5da01e32))
* Update data copy clear script to remove functions, view and sequences (DBTP-2150) ([#903](https://github.com/uktrade/platform-tools/issues/903)) ([578ef39](https://github.com/uktrade/platform-tools/commit/578ef39233dfeea4b14ac990611f8c30e520001e))

## [15.4.2](https://github.com/uktrade/platform-tools/compare/15.4.1...15.4.2) (2025-06-26)


### Bug Fixes

* Fix codestar in database copy (off-ticket) ([#900](https://github.com/uktrade/platform-tools/issues/900)) ([eb4655d](https://github.com/uktrade/platform-tools/commit/eb4655dd7a46b439c74a5a7935a3d6c0831a953d))

## [15.4.1](https://github.com/uktrade/platform-tools/compare/15.4.0...15.4.1) (2025-06-25)


### Bug Fixes

* Fix perms and workflows (off-ticket) ([#898](https://github.com/uktrade/platform-tools/issues/898)) ([2c561f2](https://github.com/uktrade/platform-tools/commit/2c561f26084290db23e049482af6ad97a8ea5980))

## [15.4.0](https://github.com/uktrade/platform-tools/compare/15.3.0...15.4.0) (2025-06-25)


### Features

* Update Datadog terraform module with handling of multiple services in platform-config (DBTP-2109) ([#890](https://github.com/uktrade/platform-tools/issues/890)) ([23c2ddd](https://github.com/uktrade/platform-tools/commit/23c2ddd13489ca766ef2dd64a6f9943498bd13e9))


### Bug Fixes

* Add permission to WAF Origin verification secret rotation lambda (off-ticket) ([#896](https://github.com/uktrade/platform-tools/issues/896)) ([041e790](https://github.com/uktrade/platform-tools/commit/041e7908cd29f20c070d3b7abcb9bc6fd92dd0ba))
* Private repos fix codestar connection in buildspec (DBTP-2100) ([#893](https://github.com/uktrade/platform-tools/issues/893)) ([9e058bc](https://github.com/uktrade/platform-tools/commit/9e058bc7a8c2f990bf45b36920fd15b4b5015016))
* Watching ECR pushes where branch name contains a / (DBTP-2124) ([#892](https://github.com/uktrade/platform-tools/issues/892)) ([31f1dac](https://github.com/uktrade/platform-tools/commit/31f1dacc5dce0d9036c2d5cc74a1af5feea1bc1d))

## [15.3.0](https://github.com/uktrade/platform-tools/compare/15.2.2...15.3.0) (2025-06-19)


### Features

* Platform-helper internal repo changes (DBTP-2100) ([#889](https://github.com/uktrade/platform-tools/issues/889)) ([9faad52](https://github.com/uktrade/platform-tools/commit/9faad5250a6fe3c67330359c05a1b9c51a071fc0))


### Bug Fixes

* Retrieve only available codestar connections (DBTP-2000) ([#880](https://github.com/uktrade/platform-tools/issues/880)) ([ef94137](https://github.com/uktrade/platform-tools/commit/ef94137772d728e9806b4746d0a62f4db233842c))

## [15.2.2](https://github.com/uktrade/platform-tools/compare/15.2.1...15.2.2) (2025-06-05)


### Bug Fixes

* Overly permissive kms key policy (DBTP-1341) ([#881](https://github.com/uktrade/platform-tools/issues/881)) ([c4f3f73](https://github.com/uktrade/platform-tools/commit/c4f3f732dcb169505394de900b493d2c646be3b9))

## [15.2.1](https://github.com/uktrade/platform-tools/compare/15.2.0...15.2.1) (2025-06-02)


### Bug Fixes

* Add --force flag to copilot svc deploy (DBTP-2003) ([#877](https://github.com/uktrade/platform-tools/issues/877)) ([26d305c](https://github.com/uktrade/platform-tools/commit/26d305cc4690ef53394bae24abe36f066eb47db6))
* Deploy specific commit tag (DBTP-1824) ([#879](https://github.com/uktrade/platform-tools/issues/879)) ([a1930ca](https://github.com/uktrade/platform-tools/commit/a1930ca5883a25a06dd303e5921975767c52591f))
* Plans fail validation (DBTP-2061) ([#876](https://github.com/uktrade/platform-tools/issues/876)) ([cc6d066](https://github.com/uktrade/platform-tools/commit/cc6d066197975a9201efa0d2cfd572ec13475f44))

## [15.2.0](https://github.com/uktrade/platform-tools/compare/15.1.0...15.2.0) (2025-05-22)


### Features

* Add repository URL to Datadog service metadata (DBTP-1919) ([#869](https://github.com/uktrade/platform-tools/issues/869)) ([0064054](https://github.com/uktrade/platform-tools/commit/00640549a20fb1cbceee4568371815f7f41635fd))
* Terraform conduit without copilot (DBTP-1927) ([#872](https://github.com/uktrade/platform-tools/issues/872)) ([d8173cb](https://github.com/uktrade/platform-tools/commit/d8173cb28a572055dffd8bacb8dc32dcfe37abed))


### Bug Fixes

* ECR repo tag mismatch (DBTP-2071) ([#875](https://github.com/uktrade/platform-tools/issues/875)) ([b0111de](https://github.com/uktrade/platform-tools/commit/b0111defa12cac07ae4862dca486283d09a562bf))

## [15.1.0](https://github.com/uktrade/platform-tools/compare/15.0.0...15.1.0) (2025-04-30)


### Features

* Retrieve python-requests lambda layer & assign to lambda function (DBTP-1915) ([#862](https://github.com/uktrade/platform-tools/issues/862)) ([ca4d2cb](https://github.com/uktrade/platform-tools/commit/ca4d2cb703c505a02746dac70be7dc1cc44a3a8c))

## [15.0.0](https://github.com/uktrade/platform-tools/compare/14.2.0...15.0.0) (2025-04-24)


### ⚠ BREAKING CHANGES

* Sort list of subnets for Opensearch (DBTP-1994) ([#856](https://github.com/uktrade/platform-tools/issues/856))

### Bug Fixes

* Do not validate config in the version command (DBTP-2016) ([#867](https://github.com/uktrade/platform-tools/issues/867)) ([5ca2ce5](https://github.com/uktrade/platform-tools/commit/5ca2ce5431202f4d94f87c63181c04c327852f4d))
* Sort list of subnets for Opensearch (DBTP-1994) ([#856](https://github.com/uktrade/platform-tools/issues/856)) ([019cefa](https://github.com/uktrade/platform-tools/commit/019cefab6d3ec172e9b012e0bb6708449e84e86b))


### Features

* Restrict trust policies for CodePipeline & CodeBuild IAM roles (DBTP-1945) ([#852](https://github.com/uktrade/platform-tools/issues/852)) ([d0e00bf](https://github.com/uktrade/platform-tools/commit/d0e00bfaa8680a3c2f5955a077c349b0db129486))

## [14.2.0](https://github.com/uktrade/platform-tools/compare/14.1.1...14.2.0) (2025-04-23)


### Features

* Deprecate platform helper notify environment progress (DBTP-1221) ([#842](https://github.com/uktrade/platform-tools/issues/842)) ([167f235](https://github.com/uktrade/platform-tools/commit/167f23591f26c3bcb1f4fd8a3218140e8f17e744))


### Bug Fixes

* Add in moving major and minor version tags to the release (DBTP-1939) ([#861](https://github.com/uktrade/platform-tools/issues/861)) ([4e8f558](https://github.com/uktrade/platform-tools/commit/4e8f5586aa69aff5a013592516faab4b5f641141))
* Add missing ECR policy (DBTP-1837) ([#857](https://github.com/uktrade/platform-tools/issues/857)) ([8add310](https://github.com/uktrade/platform-tools/commit/8add310b471417541f119ff3c2ae4cd37c626e5a))

## [14.1.1](https://github.com/uktrade/platform-tools/compare/14.1.0...14.1.1) (2025-04-17)


### Bug Fixes

* Reinstate version command (DBTP-2006) ([#858](https://github.com/uktrade/platform-tools/issues/858)) ([eec2de7](https://github.com/uktrade/platform-tools/commit/eec2de700a994e509ea696a349c5ba7501cbb444))

## [14.1.0](https://github.com/uktrade/platform-tools/compare/14.0.0...14.1.0) (2025-04-16)


### Features

* Python 3.13 support (off-ticket) ([#850](https://github.com/uktrade/platform-tools/issues/850)) ([1370c85](https://github.com/uktrade/platform-tools/commit/1370c85fe01ec7c48f86508ad24d7072fb9c2186))
* Updates to software catalog service names (DBTP-1999) ([#855](https://github.com/uktrade/platform-tools/issues/855)) ([65d84a3](https://github.com/uktrade/platform-tools/commit/65d84a32159a3f0de0ced7716d47bfb7927806af))


### Bug Fixes

* Fix error parsing platform-helper version number (off-ticket) ([#854](https://github.com/uktrade/platform-tools/issues/854)) ([ba62201](https://github.com/uktrade/platform-tools/commit/ba622015c57ff29c1af0d2d6a5370278f7edaa9c))

## [14.0.0](https://github.com/uktrade/platform-tools/compare/13.4.1...14.0.0) (2025-04-15)


### ⚠ BREAKING CHANGES

* Force version 14.0.0 (DBTP-1842) ([#845](https://github.com/uktrade/platform-tools/issues/845))

### Features

* Add env var override to pipeline generate (DBTP-1842) ([#846](https://github.com/uktrade/platform-tools/issues/846)) ([e824764](https://github.com/uktrade/platform-tools/commit/e824764b90bab0ee1ef20fd42de151596e60d81a))
* Add env var version override (DBTP-1578) ([#849](https://github.com/uktrade/platform-tools/issues/849)) ([480db28](https://github.com/uktrade/platform-tools/commit/480db280d69767b7c2ffac757e010aa38315698b))
* Allow `codebase build` to be run outside the application repository (off-ticket) ([#809](https://github.com/uktrade/platform-tools/issues/809)) ([5ec3bdf](https://github.com/uktrade/platform-tools/commit/5ec3bdf7c8aced0fc45c2bb9e6db7f124fceca7e))
* Force version 14.0.0 (DBTP-1842) ([#845](https://github.com/uktrade/platform-tools/issues/845)) ([4b5dc1e](https://github.com/uktrade/platform-tools/commit/4b5dc1ef96f1a80c67ef7cfd067ed220dbcc2be9))
* Merge in terraform-platform-modules (DBTP-1842) ([#792](https://github.com/uktrade/platform-tools/issues/792)) ([32b1ce0](https://github.com/uktrade/platform-tools/commit/32b1ce098e0bc8d37e8cc41f8bd258c5b8714ea0))


### Bug Fixes

* Correct Redis subscription filter naming (DBTP-1920) ([#847](https://github.com/uktrade/platform-tools/issues/847)) ([e872be9](https://github.com/uktrade/platform-tools/commit/e872be9f967094be6fad5df902f024d39d1148df))
* Removed unnecessary 'null' from empty values in platform-config. (DBTP-1952) ([#848](https://github.com/uktrade/platform-tools/issues/848)) ([c261a8e](https://github.com/uktrade/platform-tools/commit/c261a8e1b754c63842d496f504a0bcdc032f6167))

## [13.4.1](https://github.com/uktrade/platform-tools/compare/13.4.0...13.4.1) (2025-04-04)


### Bug Fixes

* Maintenance Page - Listener Rule cannot have more than 5 conditions (DBTP-1975) ([#836](https://github.com/uktrade/platform-tools/issues/836)) ([8d4d0cb](https://github.com/uktrade/platform-tools/commit/8d4d0cba11f02e817f672a2cf7458b5faea1465c))

## [13.4.0](https://github.com/uktrade/platform-tools/compare/13.3.0...13.4.0) (2025-04-02)


### Features

* Allow manual releases based on image reference (DBTP-1165) ([#807](https://github.com/uktrade/platform-tools/issues/807)) ([1a029a1](https://github.com/uktrade/platform-tools/commit/1a029a1d97973e07baac25e3781ec9ee5cbf2cdb))

## [13.3.0](https://github.com/uktrade/platform-tools/compare/13.2.0...13.3.0) (2025-03-31)


### Features

* Add deploy repository branch to pipeline generate (DBTP-1896) ([#814](https://github.com/uktrade/platform-tools/issues/814)) ([f4e91b2](https://github.com/uktrade/platform-tools/commit/f4e91b2a43be784b02a2e6308cdac4a8c6b8a796))
* Add new field for Datadog ticket (DBTP-1879) ([#823](https://github.com/uktrade/platform-tools/issues/823)) ([2465b1c](https://github.com/uktrade/platform-tools/commit/2465b1cb4860ac6bbd0a4faf884666a4781a4f8b))
* Allow command options to be set via environment variables (off-ticket) ([#819](https://github.com/uktrade/platform-tools/issues/819)) ([d79deb0](https://github.com/uktrade/platform-tools/commit/d79deb04a5ad0e38dfea1df91837beaee419fbb8))


### Bug Fixes

* Correctly resolve versions in config validate table output (off-ticket) ([#818](https://github.com/uktrade/platform-tools/issues/818)) ([d5bf3ff](https://github.com/uktrade/platform-tools/commit/d5bf3fff7a58fcf60a570495ed568cc77aad8b83))
* From and to account properties no longer required (DBTP-1847) ([#825](https://github.com/uktrade/platform-tools/issues/825)) ([5fa037d](https://github.com/uktrade/platform-tools/commit/5fa037da3bc587b1db61a4746f9475345ae83319))
* Initialise missing parameter provider for codebase commands (off-ticket) ([#812](https://github.com/uktrade/platform-tools/issues/812)) ([7e32663](https://github.com/uktrade/platform-tools/commit/7e326637da0fa2f630b289a9bb5bac59c02ae66e))
* Intermittent failures when calling via requests library (off-ticket) ([#826](https://github.com/uktrade/platform-tools/issues/826)) ([84a22dd](https://github.com/uktrade/platform-tools/commit/84a22dd5234587864b53d68ef6163f4d84147181))
* Update jinja2 for dependabot vulnerability fix ([#804](https://github.com/uktrade/platform-tools/issues/804)) ([66a5959](https://github.com/uktrade/platform-tools/commit/66a59598411349b8abcd4451dbf523dce2c76ac3))


### Documentation

* Add initial contributing guidelines (off-ticket) ([#811](https://github.com/uktrade/platform-tools/issues/811)) ([6c4357d](https://github.com/uktrade/platform-tools/commit/6c4357dcb5e4d245eca7caa2f403de3c498c63e8))
* Correct typo in CONTRIBUTING.md (off-ticket) ([#815](https://github.com/uktrade/platform-tools/issues/815)) ([19e61fe](https://github.com/uktrade/platform-tools/commit/19e61fed7a16cc36e7dce1a24b508efe10315140))

## [13.2.0](https://github.com/uktrade/platform-tools/compare/13.1.2...13.2.0) (2025-03-07)


### Features

* DBTP-1845 Improve Maintenance Page logging ([#790](https://github.com/uktrade/platform-tools/issues/790)) ([9fb3985](https://github.com/uktrade/platform-tools/commit/9fb39854ed31ebcc09dfe71e09ef2de3d02eb72f))


### Bug Fixes

* config validate command - wrong provider injected into PlatformHelperVersioning ([#801](https://github.com/uktrade/platform-tools/issues/801)) ([7a7c36d](https://github.com/uktrade/platform-tools/commit/7a7c36da8d6eab0111386553c64d6ba25bccc6c1))
* DBTP-1804 - Update manual release pipeline name ([#781](https://github.com/uktrade/platform-tools/issues/781)) ([cb571fc](https://github.com/uktrade/platform-tools/commit/cb571fc9985d823801a83440b03fa3f458b85eac))
* mock aws session in copilot tests ([#796](https://github.com/uktrade/platform-tools/issues/796)) ([9ee43b5](https://github.com/uktrade/platform-tools/commit/9ee43b51c9c1718f9e81d0ebe0ed2ce6364cc854))

## [13.1.2](https://github.com/uktrade/platform-tools/compare/13.1.1...13.1.2) (2025-02-26)


### Bug Fixes

* Fix Vulnerable OpenSSL included in cryptography wheels ([#786](https://github.com/uktrade/platform-tools/issues/786)) ([b6f1cb6](https://github.com/uktrade/platform-tools/commit/b6f1cb615fe8f7d59f53cb4330fd16550f710489))
* Fix load balancer tag description limit by chunking ([#784](https://github.com/uktrade/platform-tools/issues/784)) ([3ee9eae](https://github.com/uktrade/platform-tools/commit/3ee9eaece39e1483baf41e6b3d628ca143d76368))

## [13.1.1](https://github.com/uktrade/platform-tools/compare/13.1.0...13.1.1) (2025-02-21)


### Bug Fixes

* DBTP-1700 Deprecate cross_enviroment_service_access application property ([#780](https://github.com/uktrade/platform-tools/issues/780)) ([8a54526](https://github.com/uktrade/platform-tools/commit/8a5452678f71a6ee306db70d2a1c0bf079eca7b6))

## [13.1.0](https://github.com/uktrade/platform-tools/compare/13.0.2...13.1.0) (2025-02-20)


### Features

* add deploy_repository as an optional key to platform-config.yml. ([#762](https://github.com/uktrade/platform-tools/issues/762)) ([9f69b32](https://github.com/uktrade/platform-tools/commit/9f69b324faf1e3f4c18c1ebb582fab0518c9d771))
* DBTP-1788 Add deploy_repository key to codebase pipeline ([#777](https://github.com/uktrade/platform-tools/issues/777)) ([cf4e52a](https://github.com/uktrade/platform-tools/commit/cf4e52a86ba78725d3bd1380fad86ba433b035e6))


### Bug Fixes

* DBTP-1789 - Default pipelines config to empty list ([#772](https://github.com/uktrade/platform-tools/issues/772)) ([f109139](https://github.com/uktrade/platform-tools/commit/f109139b12239b30ec53c83fa220dc3b6e547ca7))
* DBTP-1792 Set FileProvider default in CopilotTemplating ([#769](https://github.com/uktrade/platform-tools/issues/769)) ([81401e6](https://github.com/uktrade/platform-tools/commit/81401e60326126a56c01aa0736789bc9a7ac0f00))
* Use fakefs in test to avoid message changing to 'overwritten' in subsequent test runs ([#775](https://github.com/uktrade/platform-tools/issues/775)) ([433592e](https://github.com/uktrade/platform-tools/commit/433592e1655ac4bcfaf2adc2ae9e1eff80a574b7))

## [13.0.2](https://github.com/uktrade/platform-tools/compare/13.0.1...13.0.2) (2025-02-10)


### Bug Fixes

* DBTP-1387 Fix maintenance page offline command when specifiying a specific service ([#746](https://github.com/uktrade/platform-tools/issues/746)) ([b22630b](https://github.com/uktrade/platform-tools/commit/b22630be5fb4cf2085c2da370e63dcd1ce6dcdc7))
* DBTP-1602 Fix resource renaming bug ([#759](https://github.com/uktrade/platform-tools/issues/759)) ([c968433](https://github.com/uktrade/platform-tools/commit/c968433d2225ca5775263bfbfa2426d856c422f7))
* DBTP-1784: Passing a full path as the first mkfile parameter causes a file not found error ([#768](https://github.com/uktrade/platform-tools/issues/768)) ([ef126c6](https://github.com/uktrade/platform-tools/commit/ef126c680a6d1812df672f39c61c508672f7eb53))
* Delete old manifest before creating json one ([#764](https://github.com/uktrade/platform-tools/issues/764)) ([681d487](https://github.com/uktrade/platform-tools/commit/681d487508d91360d8295e6cb87e0aba27788244))

## [13.0.1](https://github.com/uktrade/platform-tools/compare/13.0.0...13.0.1) (2025-01-31)


### Bug Fixes

* DBPT-1729 - Allows Vpc to be returned without security groups ([#747](https://github.com/uktrade/platform-tools/issues/747)) ([2685797](https://github.com/uktrade/platform-tools/commit/2685797d1e8b25ce2008483e0d33f6cd0627fa8d))

## [13.0.0](https://github.com/uktrade/platform-tools/compare/12.6.0...13.0.0) (2025-01-29)


### ⚠ BREAKING CHANGES

* Update release version 13.0.0 ([#743](https://github.com/uktrade/platform-tools/issues/743))

### Features

* DBTP-1505 Generate terraform codebase pipeline configuration. ([#723](https://github.com/uktrade/platform-tools/issues/723)) ([96c6d7d](https://github.com/uktrade/platform-tools/commit/96c6d7d4c070fa8f9e13ffedc23a86aa7e75d28c))
* Update release version 13.0.0 ([#743](https://github.com/uktrade/platform-tools/issues/743)) ([1eec27f](https://github.com/uktrade/platform-tools/commit/1eec27f0d14b05c722da6c696ddf98d97a4a2cde))


### Bug Fixes

* DBTP-1553  Listener rule cleanup on exception during maintenance page set up ([#737](https://github.com/uktrade/platform-tools/issues/737)) ([bb4a38f](https://github.com/uktrade/platform-tools/commit/bb4a38fe0be53a2943d1bd297d3bbeba1f8cea6c))

## [12.6.0](https://github.com/uktrade/platform-tools/compare/12.5.1...12.6.0) (2025-01-28)


### Features

* DBTP-1635 Add additional S3 source bucket validation  ([#738](https://github.com/uktrade/platform-tools/issues/738)) ([f6f65d4](https://github.com/uktrade/platform-tools/commit/f6f65d4b2e53e80dcf073605f0b975cd01c0236c))


### Bug Fixes

* DBTP-1700 Increase indent on COMMAND.md list ([#739](https://github.com/uktrade/platform-tools/issues/739)) ([9987a20](https://github.com/uktrade/platform-tools/commit/9987a20811f7fc18ba1e07487220b29e059f592d))
* use get_rules_tag_descriptions method to get descriptions ([#730](https://github.com/uktrade/platform-tools/issues/730)) ([e4dc724](https://github.com/uktrade/platform-tools/commit/e4dc7245a1db1048634bacfec791639569a237a2))


### Documentation

* DBTP-1332 Nest commands list for easier navigation ([#734](https://github.com/uktrade/platform-tools/issues/734)) ([d9bbe41](https://github.com/uktrade/platform-tools/commit/d9bbe4182e401a6d331d04ae929ab840dde82be0))

## [12.5.1](https://github.com/uktrade/platform-tools/compare/12.5.0...12.5.1) (2025-01-17)


### Bug Fixes

* DBTP-1644: handle next token when getting services for application ([#721](https://github.com/uktrade/platform-tools/issues/721)) ([b87e532](https://github.com/uktrade/platform-tools/commit/b87e532a7d53ef60bf8939c515bbac0d52cb7438))
* DBTP-1645 - conduit out of memory when querying large data sets ([#726](https://github.com/uktrade/platform-tools/issues/726)) ([d38441a](https://github.com/uktrade/platform-tools/commit/d38441ac9290883f2a0be45594b494b0d923e23f))

## [12.5.0](https://github.com/uktrade/platform-tools/compare/12.4.1...12.5.0) (2025-01-08)


### Features

* S3 cross account policy templating ([#696](https://github.com/uktrade/platform-tools/issues/696)) ([b85fb60](https://github.com/uktrade/platform-tools/commit/b85fb60ad223b93515bf0a5f3fd4ef2a018c9783))


### Bug Fixes

* DBTP-1641 - Add missing postgres plans to validation schema ([#710](https://github.com/uktrade/platform-tools/issues/710)) ([bacee31](https://github.com/uktrade/platform-tools/commit/bacee3189e430458027882e57d5facfcbf65ed90))
* fix for the bug introduced during merging a conflict in the previous PR ([#707](https://github.com/uktrade/platform-tools/issues/707)) ([ab9f0ab](https://github.com/uktrade/platform-tools/commit/ab9f0abae6ac6f0aa19462196871cd783c877bf0))
* Update dependencies to fix flaky E2E test ([#711](https://github.com/uktrade/platform-tools/issues/711)) ([3e4ac8a](https://github.com/uktrade/platform-tools/commit/3e4ac8aca348e4ee0b5aa9afc3b751fc15282be5))

## [12.4.1](https://github.com/uktrade/platform-tools/compare/12.4.0...12.4.1) (2024-12-11)


### Bug Fixes

* DBTP-1290 - fix red herring "Not a Git repository" error ([#682](https://github.com/uktrade/platform-tools/issues/682)) ([bbc7dcd](https://github.com/uktrade/platform-tools/commit/bbc7dcdfa1a47a92ed86126526d509ad8d5897eb))
* DBTP-1509 Correct link to maintenance pages instructions ([#686](https://github.com/uktrade/platform-tools/issues/686)) ([58aca89](https://github.com/uktrade/platform-tools/commit/58aca89a46207d4494a3981e0b678d0a43fef960))
* DBTP-1605 adding new key for parameter ([#690](https://github.com/uktrade/platform-tools/issues/690)) ([93a0a94](https://github.com/uktrade/platform-tools/commit/93a0a9476a09e7a1d15154df0233f28240634ec5))
* DBTP-1605 checking new param ([#689](https://github.com/uktrade/platform-tools/issues/689)) ([b7ef4a4](https://github.com/uktrade/platform-tools/commit/b7ef4a4a080e6857a777ac80df749665aa5ff30a))


### Documentation

* Correct entry in changelog ([#674](https://github.com/uktrade/platform-tools/issues/674)) ([cb0832d](https://github.com/uktrade/platform-tools/commit/cb0832de64efc556f3c812a3f4291f8e45fccb70))

## [12.4.0](https://github.com/uktrade/platform-tools/compare/12.3.0...12.4.0) (2024-12-06)


### Features

* DBTP-1568 - Add s3 support for cross environment service access ([#654](https://github.com/uktrade/platform-tools/issues/654)) ([7e1d75f](https://github.com/uktrade/platform-tools/commit/7e1d75f95cacb68e01f0f62448359166509c20b0))


### Bug Fixes

* DBTP-1498 - Add option for database dump filename ([#681](https://github.com/uktrade/platform-tools/issues/681)) ([d06ddcc](https://github.com/uktrade/platform-tools/commit/d06ddcc0253a76950f54b881af84be14b0981b66))
* DBTP-1498 - Add validation for database copy pipeline ([#683](https://github.com/uktrade/platform-tools/issues/683)) ([cda1e7b](https://github.com/uktrade/platform-tools/commit/cda1e7bc9daa1732e9032c7d6566716e3151b961))


### Documentation

* Document new dbt-platform-helper architecture ([#669](https://github.com/uktrade/platform-tools/issues/669)) ([ae4862d](https://github.com/uktrade/platform-tools/commit/ae4862da9e3e3d39c82c99222fa21450191f260a))

## [12.3.0](https://github.com/uktrade/platform-tools/compare/12.2.4...12.3.0) (2024-12-03)


### Features

* DBTP-1299 - Cross account database copy ([#657](https://github.com/uktrade/platform-tools/issues/657)) ([7d35599](https://github.com/uktrade/platform-tools/commit/7d35599533b55f15fb08801c50ce538a8a32b847))


### Refactor

* Improving provider structure and exception handling" ([#670](https://github.com/uktrade/platform-tools/issues/670)) ([331e8b8](https://github.com/uktrade/platform-tools/commit/331e8b89d60fec4e29a9ea4473ffa44cba8e92c7))

## [12.2.4](https://github.com/uktrade/platform-tools/compare/12.2.3...12.2.4) (2024-12-02)


### Bug Fixes

* DBTP-1572 - Fix _validate_exension_supported_versions incorrectly raising an error when no version is supplied ([#660](https://github.com/uktrade/platform-tools/issues/660)) ([2ce98bf](https://github.com/uktrade/platform-tools/commit/2ce98bfdcd22b880867306e3181f4815e46c6acb))

## [12.2.3](https://github.com/uktrade/platform-tools/compare/12.2.2...12.2.3) (2024-11-29)


### Bug Fixes

* DBTP-1524 Make subnet order from environment generate match CloudFormation exports ([#665](https://github.com/uktrade/platform-tools/issues/665)) ([f0f561b](https://github.com/uktrade/platform-tools/commit/f0f561beba2239f757fec62cd530483432bb953b))

## [12.2.2](https://github.com/uktrade/platform-tools/compare/12.2.1...12.2.2) (2024-11-26)


### Bug Fixes

* Fixing json loads ([#664](https://github.com/uktrade/platform-tools/issues/664)) ([46eddff](https://github.com/uktrade/platform-tools/commit/46eddff14ba2460ebe4beee1378ac75b617a8821))

## [12.2.1](https://github.com/uktrade/platform-tools/compare/12.2.0...12.2.1) (2024-11-26)


### Miscellaneous Chores

* Don't install poetry in Dockerfile.debian ([#655](https://github.com/uktrade/platform-tools/issues/655)) ([9ad8c67](https://github.com/uktrade/platform-tools/commit/9ad8c67d8abc8ad61a4123bb90d361b3e26eacd3))

## [12.2.0](https://github.com/uktrade/platform-tools/compare/12.1.0...12.2.0) (2024-11-26)


### Features

* DBTP-1395 Add validation for new slack alert channel Id that will be set in &lt;application&gt;-alb in platform-config file ([#635](https://github.com/uktrade/platform-tools/issues/635)) ([729c082](https://github.com/uktrade/platform-tools/commit/729c0821bdbc96f49c832a79bf2211475a737bf9))
* DBTP-1568 - Add s3 support for external role access ([#652](https://github.com/uktrade/platform-tools/issues/652)) ([02bebd6](https://github.com/uktrade/platform-tools/commit/02bebd6d331fd8a10cb317460a91634c5745b462))


### Bug Fixes

* DBTP-1577 Fix conduit (ecs) exec race condition  ([#656](https://github.com/uktrade/platform-tools/issues/656)) ([22eafa0](https://github.com/uktrade/platform-tools/commit/22eafa0c8388b3132663d953bf97c85887c94999))

## [12.1.0](https://github.com/uktrade/platform-tools/compare/12.0.2...12.1.0) (2024-11-21)


### Features

* DBTP-1380 Get Opensearch/Redis versions from AWS API - Platform-tools changes/Caching of AWS API calls ([#624](https://github.com/uktrade/platform-tools/issues/624)) ([72d0dd7](https://github.com/uktrade/platform-tools/commit/72d0dd70396a4632e5cb5b1f6c80b2df772a89ad))
* DBTP-1434 - CDN cache policy ([#642](https://github.com/uktrade/platform-tools/issues/642)) ([8cc2c0c](https://github.com/uktrade/platform-tools/commit/8cc2c0caf137889115c9d84c1c9895dae2a808c9))


### Reverts

* DBTP-1520 refactor conduit command ([#647](https://github.com/uktrade/platform-tools/issues/647)) ([7b56c5e](https://github.com/uktrade/platform-tools/commit/7b56c5e1a4324fbfb2585877dd38c4857c1544cc))

## [12.0.2](https://github.com/uktrade/platform-tools/compare/12.0.1...12.0.2) (2024-11-13)


### Bug Fixes

* DBTP-1534 - Removed autocompletion for the version get-platform-helper-for-project ([#631](https://github.com/uktrade/platform-tools/issues/631)) ([6da392b](https://github.com/uktrade/platform-tools/commit/6da392b2d5d3d00e5277cba69e69f837d3a3bcc8))

## [12.0.1](https://github.com/uktrade/platform-tools/compare/12.0.0...12.0.1) (2024-11-13)


### Bug Fixes

* DBTP-1548 - Maintenance page listener rules can be based on both CIDR range or IP in EGRESS_IP ssm parameter ([#625](https://github.com/uktrade/platform-tools/issues/625)) ([6712e9b](https://github.com/uktrade/platform-tools/commit/6712e9b1c12aca0bdc68f09e85b6212b7a4e1ee8))

## [12.0.0](https://github.com/uktrade/platform-tools/compare/11.4.0...12.0.0) (2024-11-11)


### ⚠ BREAKING CHANGES

* DBTP-1002 Remove support for 100% AWS Copilot version of DBT Platform ([#621](https://github.com/uktrade/platform-tools/issues/621))

#### Upgrade path

We have moved the last application off the fully AWS Copilot version of the DBT Platform Tooling. So whilst this is technically a breaking change, no action should be required on your part to upgrade from the previous major version.

### Features

* DBTP-1002 Remove support for 100% AWS Copilot version of DBT Platform ([#621](https://github.com/uktrade/platform-tools/issues/621)) ([c7a223c](https://github.com/uktrade/platform-tools/commit/c7a223c44467807eab4f68de1ee11fbc4f9b0a21))

## [11.4.0](https://github.com/uktrade/platform-tools/compare/11.3.0...11.4.0) (2024-11-08)


### Features

* DBTP-1109 Fall back on profile_account_id when trying to match account id to profile name. ([#626](https://github.com/uktrade/platform-tools/issues/626)) ([0694775](https://github.com/uktrade/platform-tools/commit/069477584930961798bf5a42ebf6c5aec60dde21))


### Documentation

* DBTP-1511 Link to Codecov in unit tests section of README ([#627](https://github.com/uktrade/platform-tools/issues/627)) ([3179945](https://github.com/uktrade/platform-tools/commit/3179945980e0fafaf94f5141abbda80cafc871bf))

## [11.3.0](https://github.com/uktrade/platform-tools/compare/11.2.0...11.3.0) (2024-11-05)


### Features

* DBTP-1431 Add validation for CDN timeout ([#609](https://github.com/uktrade/platform-tools/issues/609)) ([66a21c6](https://github.com/uktrade/platform-tools/commit/66a21c622937f7a2fc05caa75714a90ad1d82be0))

## [11.2.0](https://github.com/uktrade/platform-tools/compare/11.1.0...11.2.0) (2024-11-04)


### Features

* DBTP-1071 Generate terraform config for environment pipeline ([#611](https://github.com/uktrade/platform-tools/issues/611)) ([237fb35](https://github.com/uktrade/platform-tools/commit/237fb35fe06df7fd13e93419d282dc067187d952))


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
