# Changelog

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
