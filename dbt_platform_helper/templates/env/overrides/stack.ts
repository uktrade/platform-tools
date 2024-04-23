import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import { readFileSync } from "fs";
import { parse } from 'yaml';

interface TransformedStackProps extends cdk.StackProps {
    readonly appName: string;
    readonly envName: string;
}

export class TransformedStack extends cdk.Stack {
    public readonly template: cdk.cloudformation_include.CfnInclude;
    public readonly appName: string;
    public readonly envName: string;

    constructor(scope: cdk.App, id: string, props: TransformedStackProps) {
        super(scope, id, props);
        this.template = new cdk.cloudformation_include.CfnInclude(this, 'Template', {
            templateFile: path.join('.build', 'in.yml'),
        });
        this.appName = props.appName;
        this.envName = props.envName;

        this.uploadAddonConfiguration();
    }

    private uploadAddonConfiguration() {
        const deployRepoRoot = path.join(process.cwd(), '..', '..', '..');

        const addonConfig = parse(readFileSync(
            path.join(deployRepoRoot, 'addons.yml'),
        ).toString('utf-8'));

        new cdk.aws_ssm.CfnParameter(this, 'AddonConfig', {
            name: `/copilot/applications/${this.appName}/environments/${this.envName}/addons`,
            type: "String",
            value: JSON.stringify(addonConfig),
        });
    }
}
