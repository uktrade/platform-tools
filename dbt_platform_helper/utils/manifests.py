import yaml


def get_service_name_from_manifest(manifest_path):
    with open(manifest_path) as manifest:
        document = yaml.safe_load(manifest)
        return document["name"]


def get_repository_name_from_manifest(manifest_path):
    with open(manifest_path) as manifest:
        document = yaml.safe_load(manifest)
        image = document["image"]["location"]

        repository_with_tag = image.split("/", 1)[1]
        repository = repository_with_tag.split(":")[0]

        return repository
