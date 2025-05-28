#!/usr/bin/env python

import copy
import json
from pathlib import Path
from pathlib import PosixPath

import botocore
import botocore.errorfactory

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.copilot_environment import CopilotTemplating
from dbt_platform_helper.domain.plans import PlanLoader
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.kms import KMSProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.template import ADDON_TEMPLATE_MAP
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import validate_addons


class Copilot:

    PACKAGE_DIR = Path(__file__).resolve().parent.parent

    SERVICE_TYPES = [
        "Load Balanced Web Service",
        "Backend Service",
        "Request-Driven Web Service",
        "Static Site",
        "Worker Service",
    ]

    def __init__(
        self,
        config_provider: ConfigProvider,
        parameter_provider: ParameterStore,
        file_provider: FileProvider,
        copilot_templating: CopilotTemplating,
        kms_provider: KMSProvider,
        session,
        io: ClickIOProvider = ClickIOProvider(),
        plan_manager: PlanLoader = PlanLoader(),
        yaml_file_provider: YamlFileProvider = YamlFileProvider,
    ):
        self.config_provider = config_provider
        self.parameter_provider = parameter_provider
        self.file_provider = file_provider
        self.copilot_templating = copilot_templating
        self.kms_provider = kms_provider
        self.io = io
        self.plan_manager = plan_manager
        self.yaml_file_provider = yaml_file_provider
        self.session = session

    def make_addons(self):
        config = self.config_provider.load_and_validate_platform_config()

        templates = setup_templates()
        extensions = self._get_extensions()
        application_name = get_application_name()

        self.io.info("\n>>> Generating Terraform compatible addons CloudFormation\n")

        output_dir = Path(".").absolute()
        env_path = Path(f"copilot/environments/")
        env_addons_path = env_path / "addons"
        env_overrides_path = env_path / "overrides"

        self._cleanup_old_files(extensions, output_dir, env_addons_path, env_overrides_path)
        self._generate_env_overrides(output_dir)

        svc_names = self._list_copilot_local_services()
        base_path = Path(".")
        for svc_name in svc_names:
            self._generate_svc_overrides(base_path, templates, svc_name)

        services = []
        for ext_name, ext_data in extensions.items():
            extension = {**ext_data}
            addon_type = extension.pop("type")
            environments = extension.pop("environments")
            environment_addon_config = {
                "addon_type": addon_type,
                "environments": environments,
                "name": extension.get("name", None) or ext_name,
                "prefix": camel_case(ext_name),
                "secret_name": ext_name.upper().replace("-", "_"),
                **extension,
            }

            services.append(environment_addon_config)

            service_addon_config = {
                "application_name": application_name,
                "name": extension.get("name", None) or ext_name,
                "prefix": camel_case(ext_name),
                "environments": environments,
                **extension,
            }

            log_destination_arns = self._get_log_destination_arn()

            if addon_type in ["s3", "s3-policy"]:
                if extensions[ext_name].get("serve_static_content"):
                    continue

                s3_kms_arns = self._get_s3_kms_alias_arns(application_name, environments)
                for environment_name in environments:
                    environments[environment_name]["kms_key_arn"] = s3_kms_arns.get(
                        environment_name, "kms-key-not-found"
                    )

            self._generate_service_addons(
                extension,
                ext_name,
                addon_type,
                output_dir,
                service_addon_config,
                templates,
                log_destination_arns,
            )

        environments = self.config_provider.apply_environment_defaults(config)["environments"]

        self.copilot_templating.generate_cross_account_s3_policies(environments, extensions)

        self.io.info(templates.get_template("addon-instructions.txt").render(services=services))

    def _list_copilot_local_environments(self):
        return [
            path.parent.parts[-1] for path in Path("./copilot/environments/").glob("*/manifest.yml")
        ]

    def _is_service(self, path: PosixPath) -> bool:

        manifest_file = self.yaml_file_provider.load(path)
        if not manifest_file or not manifest_file.get("type"):
            self.io.abort_with_error(f"No type defined in manifest file {str(path)}; exiting")

        return manifest_file.get("type") in self.SERVICE_TYPES

    def _list_copilot_local_services(self):
        return [
            path.parent.parts[-1]
            for path in Path("./copilot/").glob("*/manifest.yml")
            if self._is_service(path)
        ]

    def _validate_and_normalise_extensions_config(self, config_file, key_in_config_file=None):
        """Load a config file, validate it against the extensions schemas and
        return the normalised config dict."""

        def _lookup_plan(addon_type, env_conf):
            plan = env_conf.pop("plan", None)
            conf = addon_plans[addon_type][plan] if plan else {}

            # Make a copy of the addon plan config so subsequent
            # calls do not override the root object
            conf = conf.copy()

            conf.update(env_conf)

            return conf

        def _normalise_keys(source: dict):
            return {k.replace("-", "_"): v for k, v in source.items()}

        addon_plans = self.plan_manager.load()

        # load and validate config
        config = self.yaml_file_provider.load(config_file)

        if config and key_in_config_file:
            config = config[key_in_config_file]

        # empty file
        if not config:
            return {}

        errors = validate_addons(config)

        if errors:
            self.io.error(f"Errors found in {config_file}:")
            for addon, error in errors.items():
                self.io.error(f"Addon '{addon}': {error}")
            self.io.abort_with_error("Invalid platform-config.yml provided, see above warnings")

        env_names = self._list_copilot_local_environments()
        svc_names = self._list_copilot_local_services()

        if not env_names:
            self.io.abort_with_error("No environments found in ./copilot/environments; exiting")

        if not svc_names:
            self.io.abort_with_error("No services found in ./copilot/; exiting")

        normalised_config = {}
        config_has_errors = False
        for addon_name, addon_config in config.items():
            addon_type = addon_config["type"]
            normalised_config[addon_name] = copy.deepcopy(addon_config)

            if "services" in normalised_config[addon_name]:
                if normalised_config[addon_name]["services"] == "__all__":
                    normalised_config[addon_name]["services"] = svc_names

                if not set(normalised_config[addon_name]["services"]).issubset(set(svc_names)):
                    self.io.error(
                        f"Services listed in {addon_name}.services do not exist in ./copilot/"
                    )
                    config_has_errors = True

            environments = normalised_config[addon_name].pop("environments", {})
            default = environments.pop("*", environments.pop("default", {}))

            initial = _lookup_plan(addon_type, default)

            missing_envs = set(environments.keys()) - set(env_names)
            if missing_envs:
                self.io.error(
                    f"Environment keys listed in {addon_name} do not match those defined in ./copilot/environments"
                )
                self.io.error(f"  Missing environments: {', '.join(sorted(missing_envs))}")
                config_has_errors = True

            if config_has_errors:
                continue

            normalised_environments = {}

            for env in env_names:
                normalised_environments[env] = _normalise_keys(initial)

            for env_name, env_config in environments.items():
                if env_config is None:
                    env_config = {}
                normalised_environments[env_name].update(
                    _lookup_plan(addon_type, _normalise_keys(env_config))
                )

            normalised_config[addon_name]["environments"] = normalised_environments

        if config_has_errors:
            self.io.abort_with_error("Configuration has errors. Exiting.")

        return normalised_config

    def _get_log_destination_arn(self):
        """Get destination arns stored in param store in projects aws
        account."""

        try:
            destination_arns = self.parameter_provider.get_ssm_parameter_by_name(
                "/copilot/tools/central_log_groups"
            )
        except botocore.errorfactory.ParameterNotFound:
            self.io.abort_with_error(
                "No aws central log group defined in Parameter Store at location /copilot/tools/central_log_groups; exiting"
            )

        return json.loads(destination_arns["Value"])

    def _generate_svc_overrides(self, base_path, templates, name):
        self.io.info(f"\n>>> Generating service overrides for {name}\n")
        overrides_path = base_path.joinpath(f"copilot/{name}/overrides")
        overrides_path.mkdir(parents=True, exist_ok=True)
        overrides_file = overrides_path.joinpath("cfn.patches.yml")
        overrides_file.write_text(templates.get_template("svc/overrides/cfn.patches.yml").render())

    def _get_s3_kms_alias_arns(self, application_name, config):
        application = load_application(application_name, self.session)
        arns = {}

        for environment_name in application.environments:
            kms_provider = self.kms_provider(
                application.environments[environment_name].session.client("kms")
            )

            if environment_name not in config:
                continue

            if "bucket_name" not in config[environment_name]:
                continue

            bucket_name = config[environment_name]["bucket_name"]
            alias_name = f"alias/{application_name}-{environment_name}-{bucket_name}-key"

            try:
                response = kms_provider.describe_key(alias_name)

            # Boto3 classifies all AWS service errors and exceptions as ClientError exceptions
            except botocore.exceptions.ClientError as error:
                if error.response["Error"]["Code"] == "NotFoundException":
                    pass
            else:
                arns[environment_name] = response["KeyMetadata"]["Arn"]

        return arns

    def _get_extensions(self):
        config = self._validate_and_normalise_extensions_config(
            self.PACKAGE_DIR / "default-extensions.yml"
        )
        project_config = self._validate_and_normalise_extensions_config(
            PLATFORM_CONFIG_FILE, "extensions"
        )
        config.update(project_config)
        return config

    def _generate_override_files(self, base_path, file_path, output_dir):
        def generate_files_for_dir(pattern):
            for file in file_path.glob(pattern):
                if file.is_file():
                    contents = file.read_text()
                    file_name = str(file).removeprefix(f"{file_path}/")
                    self.io.info(
                        self.file_provider.mkfile(
                            base_path,
                            output_dir / file_name,
                            contents,
                            overwrite=True,
                        )
                    )

        generate_files_for_dir("*")
        generate_files_for_dir("bin/*")

    def _generate_env_overrides(self, output_dir):
        path = "templates/env/terraform-overrides"
        self.io.info("\n>>> Generating Environment overrides\n")
        overrides_path = output_dir.joinpath(f"copilot/environments/overrides")
        overrides_path.mkdir(parents=True, exist_ok=True)
        template_overrides_path = Path(__file__).parent.parent.joinpath(path)
        self._generate_override_files(Path("."), template_overrides_path, overrides_path)

    def _generate_service_addons(
        self,
        addon_config,
        addon_name,
        addon_type,
        output_dir,
        service_addon_config,
        templates,
        log_destination_arns,
    ):
        # generate svc addons
        for addon_template in ADDON_TEMPLATE_MAP.get(addon_type, []):
            template = templates.get_template(addon_template)

            for svc in addon_config.get("services", []):
                service_path = Path(f"copilot/{svc}/addons/")

                contents = template.render(
                    {
                        "addon_config": service_addon_config,
                        "log_destination": log_destination_arns,
                    }
                )

                (output_dir / service_path).mkdir(parents=True, exist_ok=True)
                self.io.info(
                    self.file_provider.mkfile(
                        output_dir, service_path / f"{addon_name}.yml", contents, overwrite=True
                    )
                )

    def _cleanup_old_files(self, config, output_dir, env_addons_path, env_overrides_path):
        def _rmdir(path):
            if not path.exists():
                return
            for f in path.iterdir():
                if f.is_file():
                    f.unlink()
                if f.is_dir():
                    _rmdir(f)
                    f.rmdir()

        _rmdir(output_dir / env_addons_path)
        _rmdir(output_dir / env_overrides_path)

        all_services = set()
        for services in [v["services"] for v in config.values() if "services" in v]:
            all_services.update(services)

        for service in all_services:
            svc_addons_dir = Path(output_dir, "copilot", service, "addons")
            if not svc_addons_dir.exists():
                continue
            for f in svc_addons_dir.iterdir():
                if f.is_file():
                    f.unlink()
