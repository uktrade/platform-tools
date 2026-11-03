output "active_aliases" {
    description = "Map of each key version and corresponsing alias name"
    value = {
        for k, v in aws_kms_alias.container_image_signer_key : k => v.name
    }
}