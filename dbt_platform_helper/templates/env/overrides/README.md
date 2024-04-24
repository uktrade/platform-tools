# Answers to some obvious questions

## Why not regular cfn.patches.yml for the overrides?

We need to add the contents of `extensions.yml` to Parameter Store.

This is then used by is used by `platform-helper conduit` so that you don't have to be in the `*-deploy` directory to run it.

## Why TypeScript and not Python?

Because [TypeScript is what AWS Copilot supports](https://aws.github.io/copilot-cli/en/docs/developing/overrides/cdk/).
