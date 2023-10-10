import yaml


def get_service_name_from_manifest(manifest_path):
    with open(manifest_path) as manifest:
        document = yaml.safe_load(manifest)
        return document["name"]
