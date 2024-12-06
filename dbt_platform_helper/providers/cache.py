import os
from datetime import datetime
from pathlib import Path

import yaml


class CacheProvider:
    def __init__(self):
        self.cache_file = ".platform-helper-config-cache.yml"

    def read_supported_versions_from_cache(self, resource_name):

        platform_helper_config = self.__read_file_as_yaml(self.cache_file)

        return platform_helper_config.get(resource_name).get("versions")

    def write_to_cache(self, resource_name, supported_versions):

        platform_helper_config = {}

        if self.__platform_helper_cache_exists():
            platform_helper_config = self.__read_file_as_yaml(self.cache_file)

        cache_dict = {
            resource_name: {
                "versions": supported_versions,
                "date-retrieved": datetime.now().strftime("%d-%m-%y %H:%M:%S"),
            }
        }

        platform_helper_config.update(cache_dict)

        with open(self.cache_file, "w") as file:
            file.write("# [!] This file is autogenerated via the platform-helper. Do not edit.\n")
            yaml.dump(platform_helper_config, file)

    def cache_refresh_required(self, resource_name) -> bool:
        """
        Checks if the platform-helper should reach out to AWS to 'refresh' its
        cached values.

        An API call is needed if any of the following conditions are met:
            1. No cache file (.platform-helper-config.yml) exists.
            2. The resource name (e.g. redis, opensearch) does not exist within the cache file.
            3. The date-retrieved value of the cached data is > than a time interval. In this case 1 day.
        """

        if not self.__platform_helper_cache_exists():
            return True

        platform_helper_config = self.__read_file_as_yaml(self.cache_file)

        if platform_helper_config.get(resource_name):
            return self.__check_if_cached_datetime_is_greater_than_interval(
                platform_helper_config[resource_name].get("date-retrieved"), 1
            )

        return True

    @staticmethod
    def __check_if_cached_datetime_is_greater_than_interval(date_retrieved, interval_in_days):

        current_datetime = datetime.now()
        cached_datetime = datetime.strptime(date_retrieved, "%d-%m-%y %H:%M:%S")
        delta = current_datetime - cached_datetime

        return delta.days > interval_in_days

    @staticmethod
    def __read_file_as_yaml(file_name):

        return yaml.safe_load(Path(file_name).read_text())

    def __platform_helper_cache_exists(self):
        return os.path.exists(self.cache_file)
