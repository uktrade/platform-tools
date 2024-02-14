# Why not regular cfn.patches.yml for the overrides?

We need to add the contents of `addons.yml` to Parameter Store.

This is then used by is used by `copilot-helper conduit` so that you don't have to be in the `*-deploy` directory to run it.
