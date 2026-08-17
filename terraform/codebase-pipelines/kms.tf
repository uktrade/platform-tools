

locals {
  # !! Do not change this as it will break GitHub Worfklow CI/CD deployments
  static_signer_alias = "alias/${var.application}-container-image-signer-key"

  #  For key rotation, update the key_alias_mappings local:
  #
  #  1. Duplicate the current key alias object v_xx_xx_xxxx
  #  2. Update the key of the *duplicate* object to today's date
  #  3. Update the alias on the *previous* object to "${local.static_signer_alias}-<previous object key>"
  #  4. Update the description on the *previous* object to "Expired Asymmetric KMS Key for image signing and verification"
  # 
  #  e.g.
  #  v_16_08_2026 = {
  #    alias       = local.static_signer_alias
  #    description = "ECC_NIST_P256 Asymmetric KMS Key for image signing and verification"
  #  }

  key_alias_mappings = {
    v_15_08_2026 = {
      alias       = local.static_signer_alias
      description = "Asymmetric KMS Key for image signing and verification"
    }
  }
}


module "kms_signer_key" {
  source             = "./kms-signer-key"
  application        = var.application
  key_alias_mappings = local.key_alias_mappings
  deploy_account_ids = local.deploy_account_ids
  tags               = local.tags
}