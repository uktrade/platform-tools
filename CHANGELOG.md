# Changelog

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
