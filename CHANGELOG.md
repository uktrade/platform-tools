# Changelog

## [9.0.0](https://github.com/uktrade/platform-tools/compare/v8.0.0...9.0.0) (2024-04-25)


### ⚠ BREAKING CHANGES

* DBTP-885 Rename addons.yml to extensions.yml ([#413](https://github.com/uktrade/platform-tools/issues/413))
* DBTP-905 Remove unused bootstrap config files ([#406](https://github.com/uktrade/platform-tools/issues/406))
* Update aws-cdk and aws-cdk-packages to fix CVE 5777 ([#409](https://github.com/uktrade/platform-tools/issues/409))
* DBTP-905 Remove bootstrap commands and requirement for bootstrap.yml ([#402](https://github.com/uktrade/platform-tools/issues/402))
* DBTP-859 Modify make-addons to support Terraform stack ([#391](https://github.com/uktrade/platform-tools/issues/391))
* DBTP-810 Rename copilot-tools/helper to platform-tools/helper ([#365](https://github.com/uktrade/platform-tools/issues/365))
* DBTP-763 - Get copilot and copilot-helper version from file ([#336](https://github.com/uktrade/platform-tools/issues/336))
* DBTP-756 delete waf config ([#330](https://github.com/uktrade/platform-tools/issues/330))

### Features

* add `iops` property for RDS addons ([#359](https://github.com/uktrade/platform-tools/issues/359)) ([98617ae](https://github.com/uktrade/platform-tools/commit/98617ae8024479cdee66637dfe39d8e0e3eeb1a8))
* copilot-helper conduit for redis, postgres and opensearch. ([#140](https://github.com/uktrade/platform-tools/issues/140)) ([019b2ac](https://github.com/uktrade/platform-tools/commit/019b2ac916d66e3bd837345b8eba3727204ec595))
* DBTP-764 Wraps generate + make-addons in a new generate command ([#339](https://github.com/uktrade/platform-tools/issues/339)) ([4af8547](https://github.com/uktrade/platform-tools/commit/4af8547e1c3cd6a69ee648bdb70710979b2f3a39))
* DBTP-777 - Automate release version ([#395](https://github.com/uktrade/platform-tools/issues/395)) ([ce28788](https://github.com/uktrade/platform-tools/commit/ce287883bde04fab01062fb330ec76229fb2ff2a))
* DBTP-778 Slack notification on publish ([#383](https://github.com/uktrade/platform-tools/issues/383)) ([fec1ac8](https://github.com/uktrade/platform-tools/commit/fec1ac8e39255b9aaa20dd9d40bf8020543e0f24))
* DBTP-786 file based platform-tools version checks ([#369](https://github.com/uktrade/platform-tools/issues/369)) ([83a8425](https://github.com/uktrade/platform-tools/commit/83a84251c7ef571a6f2f5d0a6b3f9fcc090b6a2c))
* DBTP-859 Modify make-addons to support Terraform stack ([#391](https://github.com/uktrade/platform-tools/issues/391)) ([b3eb9db](https://github.com/uktrade/platform-tools/commit/b3eb9db2976fe337b690649b66e939336d1ccc6c))
* set the ECS cluster name ([#407](https://github.com/uktrade/platform-tools/issues/407)) ([8f6af32](https://github.com/uktrade/platform-tools/commit/8f6af32532e112a0bd550884acee98bc0ca1f654))
* Support pushing to public repositories in a pipeline. ([#366](https://github.com/uktrade/platform-tools/issues/366)) ([561ffcc](https://github.com/uktrade/platform-tools/commit/561ffcc3137b83fdc55b2a144cf945f17ce95ddc))
* task-level metrics dashboard [DBTP-698] ([#310](https://github.com/uktrade/platform-tools/issues/310)) ([7fd7d4e](https://github.com/uktrade/platform-tools/commit/7fd7d4ecfb863f6b0fb7283defca7f57ee0ea498))


### Bug Fixes

* addon plan attribute inheritance ([#352](https://github.com/uktrade/platform-tools/issues/352)) ([b964a08](https://github.com/uktrade/platform-tools/commit/b964a0831c6be6236098315c007d8f8984e8ed19))
* all addon resource names must be globally unique [DBTP-734] ([#312](https://github.com/uktrade/platform-tools/issues/312)) ([58bc4a4](https://github.com/uktrade/platform-tools/commit/58bc4a4e1242a10a152c083d5d7d62a3f493c3d4))
* allow for hyphenated service names [DBTP-741] ([#315](https://github.com/uktrade/platform-tools/issues/315)) ([e3695dd](https://github.com/uktrade/platform-tools/commit/e3695dd331325e74ebc56cfef91a97f421cf0548))
* allow setting opensearch volume size ([#191](https://github.com/uktrade/platform-tools/issues/191)) ([f5032a1](https://github.com/uktrade/platform-tools/commit/f5032a1c30d24c61be3f2a073665f8e72cfde585))
* attempt to fix expected vs actual issue ([#364](https://github.com/uktrade/platform-tools/issues/364)) ([142f00d](https://github.com/uktrade/platform-tools/commit/142f00df39488b83dc887d859167ab49daba39d8))
* bind conduit tasks to app and env ([#150](https://github.com/uktrade/platform-tools/issues/150)) ([77ebc8c](https://github.com/uktrade/platform-tools/commit/77ebc8c7a0cdbefed93fde1835c2922fe7dab6d9))
* Change import to relative to fix codebuild problems ([#387](https://github.com/uktrade/platform-tools/issues/387)) ([4008f49](https://github.com/uktrade/platform-tools/commit/4008f4991bd3b3786bf8a69449a5a06a59a5fe28))
* change volume size for rds postgres tiny plan to 20GB ([#357](https://github.com/uktrade/platform-tools/issues/357)) ([5267349](https://github.com/uktrade/platform-tools/commit/5267349956cf4469ddb1827d3abf92b34c524d0b))
* Conduit check parameter store for connection strings first ([#182](https://github.com/uktrade/platform-tools/issues/182)) ([da500fa](https://github.com/uktrade/platform-tools/commit/da500fa02af7faa00a3c12c5ac9779acbc8574d5))
* DBTP- 766 - Change version warning to alert only ([#356](https://github.com/uktrade/platform-tools/issues/356)) ([372fbb9](https://github.com/uktrade/platform-tools/commit/372fbb9b7188aae35e3a71f9e7c09ac8ab95ebb0))
* DBTP-763 - Get copilot and copilot-helper version from file ([#336](https://github.com/uktrade/platform-tools/issues/336)) ([97b6486](https://github.com/uktrade/platform-tools/commit/97b6486d827fc7553e09868e069ed89b8917d290))
* DBTP-907 Platform helper generate version file ([#403](https://github.com/uktrade/platform-tools/issues/403)) ([f386383](https://github.com/uktrade/platform-tools/commit/f386383fc511757bdf9231f0ffe3a1d8aa971461))
* DPTP-923 Mock function that causes problems in generate tests ([#411](https://github.com/uktrade/platform-tools/issues/411)) ([3eb57bf](https://github.com/uktrade/platform-tools/commit/3eb57bf35301a489bc520aad4b3c2c95ee0fd6d6))
* enable monitoring addon by default ([#313](https://github.com/uktrade/platform-tools/issues/313)) ([127348c](https://github.com/uktrade/platform-tools/commit/127348c461804473646bc8792aed208c8d55bf07))
* Ensure deprecation for make_addons is signposted in COMMANDS.md ([#384](https://github.com/uktrade/platform-tools/issues/384)) ([346bc93](https://github.com/uktrade/platform-tools/commit/346bc9332c805a68c1bc2e347425088495702f0d))
* ensure opensearch domain is created before param ([#342](https://github.com/uktrade/platform-tools/issues/342)) ([a8366e7](https://github.com/uktrade/platform-tools/commit/a8366e7754e84af1f4591d4bc7333ece9499bf31))
* Fix broken links in ReadMe files ([#379](https://github.com/uktrade/platform-tools/issues/379)) ([b77e041](https://github.com/uktrade/platform-tools/commit/b77e041d8e5f75ec74ab0ecf6a9e530069c65d4c))
* Fix buildspec.pypi.yml file ([#390](https://github.com/uktrade/platform-tools/issues/390)) ([0620a22](https://github.com/uktrade/platform-tools/commit/0620a22bb0e6dae1706d01a4257c33dab9282c46))
* Fix pipeline permissions bug ([#335](https://github.com/uktrade/platform-tools/issues/335)) ([da5362f](https://github.com/uktrade/platform-tools/commit/da5362f33fd5cdbf77847b3697a21178fc64b51e))
* Fix renaming capitalisation ([#375](https://github.com/uktrade/platform-tools/issues/375)) ([f0b9b3d](https://github.com/uktrade/platform-tools/commit/f0b9b3d8d1f4bcab7f3b5cdc22e39dc531790bde))
* lambda related resource names must be unique [DBTP-736] ([#314](https://github.com/uktrade/platform-tools/issues/314)) ([90e5159](https://github.com/uktrade/platform-tools/commit/90e515953b5660c823b25910eb3c308d6e468529))
* more url invalid symbols for passwords in urls ([#159](https://github.com/uktrade/platform-tools/issues/159)) ([999956c](https://github.com/uktrade/platform-tools/commit/999956c12a31d52bdb6166e4511b0db9d387d58a))
* opensearch access policy incorrect usage of truncate ([#153](https://github.com/uktrade/platform-tools/issues/153)) ([9189666](https://github.com/uktrade/platform-tools/commit/9189666052261356d8e3351158550cf1c7a54f77))
* OpenSearch resource access policy ARN generation ([#152](https://github.com/uktrade/platform-tools/issues/152)) ([497431f](https://github.com/uktrade/platform-tools/commit/497431f41f6f85ae0ef67e90acbfc6b966e4189b))
* otel metric collection errors ([#372](https://github.com/uktrade/platform-tools/issues/372)) ([9773361](https://github.com/uktrade/platform-tools/commit/9773361baa0e201f0f49f3012a222e027d261af0))
* paginate through hosted zones to circumvent the 100 results limit ([#382](https://github.com/uktrade/platform-tools/issues/382)) ([fa6095f](https://github.com/uktrade/platform-tools/commit/fa6095fb53564726bc30796df04e2148a807e580))
* passwords in urls with invalid characters ([#158](https://github.com/uktrade/platform-tools/issues/158)) ([ba8d4f5](https://github.com/uktrade/platform-tools/commit/ba8d4f54be121908332437ae9d9cae3dec815857))
* Properly rename the package from dbt-copilot-tools to dbt-copilot-helper ([#371](https://github.com/uktrade/platform-tools/issues/371)) ([ce05b36](https://github.com/uktrade/platform-tools/commit/ce05b361f6d9af1bb64a6736e0c0fd90a4999b55))
* Publish to Slack as standalone script ([#388](https://github.com/uktrade/platform-tools/issues/388)) ([e770e78](https://github.com/uktrade/platform-tools/commit/e770e785ec8acd35bd4ba97612e298698c390735))
* RDS parameter group family ([#354](https://github.com/uktrade/platform-tools/issues/354)) ([5f34dfd](https://github.com/uktrade/platform-tools/commit/5f34dfdad9e30dcf8fd79e360f296bb7301c172a))
* restore wrongfully removed threading ([#350](https://github.com/uktrade/platform-tools/issues/350)) ([678c525](https://github.com/uktrade/platform-tools/commit/678c5257faf2fce9af044be5d5c2a31dd4c9ef11))
* Restore yml map type ([#392](https://github.com/uktrade/platform-tools/issues/392)) ([a6cf9c8](https://github.com/uktrade/platform-tools/commit/a6cf9c8eb10ef9382a7b1a6e8c24c9c215bbd55e))
* truncate opensearch names under 20 chars ([#156](https://github.com/uktrade/platform-tools/issues/156)) ([e660e46](https://github.com/uktrade/platform-tools/commit/e660e46d3e71b27c784a0eeb348dd9b4eb0597ce))
* Update aws-cdk and aws-cdk-packages to fix CVE 5777 ([#409](https://github.com/uktrade/platform-tools/issues/409)) ([ed3fe10](https://github.com/uktrade/platform-tools/commit/ed3fe1063b3851f2b5b568976bc79a5da2f9b5f5))
* Update fixture pyproject.toml file jinja dependency ([#381](https://github.com/uktrade/platform-tools/issues/381)) ([e13ac22](https://github.com/uktrade/platform-tools/commit/e13ac22d76c6b4105398f74f88b5b57d25ceac32))


### Reverts

* "ci: Add pull request title validation ([#343](https://github.com/uktrade/platform-tools/issues/343))" ([#346](https://github.com/uktrade/platform-tools/issues/346)) ([74a20a1](https://github.com/uktrade/platform-tools/commit/74a20a112a0bcfa0bfc50b95ce4ee99447884147))


### Documentation

* DBTP-735 Expand common command parameter placeholders to full words ([#338](https://github.com/uktrade/platform-tools/issues/338)) ([ae20ad9](https://github.com/uktrade/platform-tools/commit/ae20ad9515366d7201da640bddac3c1ba9eff41d))


### Miscellaneous Chores

* DBTP-756 delete waf config ([#330](https://github.com/uktrade/platform-tools/issues/330)) ([e83a27e](https://github.com/uktrade/platform-tools/commit/e83a27e0d2b7def22b50da7b41251d2cac6c1f5b))
* DBTP-810 Rename copilot-tools/helper to platform-tools/helper ([#365](https://github.com/uktrade/platform-tools/issues/365)) ([3e77172](https://github.com/uktrade/platform-tools/commit/3e77172e5d8a32c2aabcb46f5b49a592c4a1717b))
* DBTP-885 Rename addons.yml to extensions.yml ([#413](https://github.com/uktrade/platform-tools/issues/413)) ([ecdabd7](https://github.com/uktrade/platform-tools/commit/ecdabd7cca94bd7cb4d55c866327734c22f81fb0))
* DBTP-905 Remove bootstrap commands and requirement for bootstrap.yml ([#402](https://github.com/uktrade/platform-tools/issues/402)) ([08019eb](https://github.com/uktrade/platform-tools/commit/08019eba2cf909e4ea3bae008f13ca8ee8dd3d72))
* DBTP-905 Remove unused bootstrap config files ([#406](https://github.com/uktrade/platform-tools/issues/406)) ([70e9aec](https://github.com/uktrade/platform-tools/commit/70e9aecc836094e07fc234faf9cbc7606b76ff37))

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
