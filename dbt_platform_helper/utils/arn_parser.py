from dbt_platform_helper.providers.validation import ValidationException


class ARN:
    def __init__(self, arn, *args, **kwargs):
        # store the original ARN
        self.__source = arn

        arn_parts = arn.split(":", 7)

        if len(arn_parts) != 7:
            raise ValidationException(f"Invalid ARN: {arn}")

        # parse and store ARN parts
        # arn:partition:service:region:account-id:resource-type:resource-id
        (
            _,
            partition,
            service,
            region,
            account,
            project,
            build_id,
        ) = arn_parts

        self.__partition = partition
        self.__service = service
        self.__region = region
        self.__account_id = account
        self.__project = project
        self.__build_id = build_id

    @property
    def source(self):
        return self.__source

    @property
    def partition(self):
        return self.__partition

    @property
    def service(self):
        return self.__service

    @property
    def region(self):
        return self.__region

    @property
    def account_id(self):
        return self.__account_id

    @property
    def project(self):
        return self.__project

    @property
    def build_id(self):
        return self.__build_id
