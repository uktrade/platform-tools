This runs as step three of a multi part process.
Once step 2 is complete and the `route 53` domain records are created. The domain 

# Summary

This runs as *step three* of a 4 step process.
This module runs after *step two*.

# Prerequisites
- `route 53` certificates created in *step two*


# Example:
```
module "privatelink-accept-certs" {
  source    = "../privatelink/accept-certificates"
  
  application = "application"
  environment = "environment"
}
```