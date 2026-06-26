# Summary

This runs as *step one* of a 3 step process.
The outputs of this module are required as input data for step two, setting up the source account infrastructure.

# Prerequisites
- the exact domain for the endpoint
- the calling cidr range

# Restrictions
Current Implementation restricts all set up to include a certificate and requires a `route 53` domain to be set up.


# Example:
```
module "privatelink" {
  for_each = {
    "a-to-b" = {
      domain                 = "something.uktrade.digital"
      producer_account_id    = "123456789012"
      producer_vpc_name      = "example"
      producer_application   = "application"
      producer_environment   = "dev"
      consumer_account_id      = "098765432109"
      consumer_cidr         = [
        "127.0.0.1/24"
      ]
    }
  }

  source    = "git::ssh://git@github.com/uktrade/platform-tools//terraform/privatelink/producer?depth=1&ref=15.33.0"
  # (local) source    = "../../../../platform-tools/terraform/privatelink/producer"
  providers = { aws = aws.provider }
  name      = each.key
  config    = each.value
}
```