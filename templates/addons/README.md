# Addons

Addons can exist at the service level (e.g. `copilot/web/addons/some-addon.yml`) or the environment level (e.g. `copilot/environments/addons/some-addon.yml`).

We mostly use environment addons because service are addons deleted when you delete the service, which would be bad for things like a database.

Exceptions to the above include:

* `s3-policy.yml` which needs to be attached to the service
* `waf.yml` which needs to be attached to the web facing service
