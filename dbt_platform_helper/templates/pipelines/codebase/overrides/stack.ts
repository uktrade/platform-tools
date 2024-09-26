import * as path from 'path';
import {readFileSync} from "fs";
import {execSync} from "child_process";

import {parse, stringify} from 'yaml';
import * as cdk from 'aws-cdk-lib';

import {
    CodeStarConnectionListConnectionsOutput,
    PipelineManifest,
    PipelinesConfiguration,
    TransformedStackProps
} from "./types";

export class TransformedStack extends cdk.Stack {
    public readonly template: cdk.cloudformation_include.CfnInclude;
    public readonly appName: string;
    private pipelineManifest: PipelineManifest;
    private codestarConnection: { arn: string; id: string; };
    private deployRepository: string;
    private codebaseConfiguration: PipelinesConfiguration['codebase_pipelines'][0];
    private pipelinesFile: PipelinesConfiguration;

    constructor(scope: cdk.App, id: string, props: TransformedStackProps) {
        super(scope, id, props);
        this.template = new cdk.cloudformation_include.CfnInclude(this, 'Template', {
            templateFile: path.join('.build', 'in.yml'),
        });
        this.appName = props.appName;

        // Load external configuration
        this.loadManifestFiles();
        this.loadCodestarConnection();
        this.loadGitRemote();

        // Alter cloudformation template
        this.createImageBuildProject();
        this.createECRRepository();
        this.createEventRuleRole();
        this.updatePipelineBuildProject();
        this.updatePipelines();
        this.allowBuildProjectToUseCodestarConnection();
        this.allowPipelineToDescribeECRImages();
        this.allowPipelineToUseEnvManagerRole();
        this.allowBuildProjectToUseEnvManagerRole();
        this.uploadPipelineConfiguration();
    }

    private createImageBuildProject() {
        const filterGroups: Array<Array<{ type: string, pattern: string; }>> = [];
        const watchedBranches = new Set(
            this.codebaseConfiguration.pipelines.map(p => p.branch)
                .filter(p => !!p),
        );

        for (const branch of watchedBranches) {
            let sanitisedBranch = branch;

            if (branch?.endsWith('*')){
                sanitisedBranch?.replace('*', '.*');
            } else {
                sanitisedBranch = sanitisedBranch?.concat('$');
            }

            filterGroups.push([
                {type: 'EVENT', pattern: 'PUSH'},
                {type: 'HEAD_REF', pattern: `^refs/heads/${sanitisedBranch}`},
            ]);
        }

        if (this.codebaseConfiguration.pipelines.some(p => p.tag)) {
            filterGroups.push([
                {type: 'EVENT', pattern: 'PUSH'},
                {type: 'HEAD_REF', pattern: '^refs/tags/.*'},
            ]);
        }

        const envVars = [
            {name: 'AWS_ACCOUNT_ID', value: this.account},
            {name: 'ECR_REPOSITORY', value: this.ecrRepository()},
            {name: 'CODESTAR_CONNECTION_ARN', value: this.codestarConnection.arn},
        ];
        if (this.additionalEcrRepository()){
            envVars.push({name: 'ADDITIONAL_ECR_REPOSITORY', value: this.additionalEcrRepository()});
        }

        const imageBuildProject: cdk.aws_codebuild.CfnProject = new cdk.aws_codebuild.CfnProject(this, 'ImageBuildProject', {
            name: `codebuild-${this.appName}-${this.pipelineManifest.name}`,
            description: `Publish images on push to ${this.codebaseConfiguration.repository}`,
            badgeEnabled: true,
            encryptionKey: cdk.Fn.importValue(`${this.appName}-ArtifactKey`),
            serviceRole: this.template.getResource('BuildProjectRole').getAtt('Arn').toString(),
            timeoutInMinutes: 30,
            visibility: 'PRIVATE',
            artifacts: {
                type: 'NO_ARTIFACTS',
            },
            cache: {
                modes: ['LOCAL_DOCKER_LAYER_CACHE'],
                type: 'LOCAL',
            },
            triggers: {
                buildType: 'BUILD',
                filterGroups,
                webhook: true,
            },
            environment: {
                type: 'LINUX_CONTAINER',
                computeType: 'BUILD_GENERAL1_SMALL',
                privilegedMode: true,
                image: 'public.ecr.aws/uktrade/ci-image-builder:tag-latest',
                environmentVariables: envVars,
            },
            source: {
                type: 'GITHUB',
                location: `https://github.com/${this.codebaseConfiguration.repository}.git`,
                gitCloneDepth: 0,
                auth: {type: 'OAUTH'},
                gitSubmodulesConfig: {fetchSubmodules: false},
                buildSpec: stringify(parse(
                    readFileSync(path.join(__dirname, 'buildspec.image.yml')).toString('utf-8'),
                )),
            },
        });

        imageBuildProject.node.addDependency(this.template.getResource("BuildProjectRole") as cdk.aws_iam.CfnRole);
        imageBuildProject.node.addDependency(this.template.getResource("BuildProjectPolicy") as cdk.aws_iam.CfnPolicy);
    }

    private createECRRepository() {
        new cdk.aws_ecr.CfnRepository(this, 'ECRRepository', {
            repositoryName: `${this.appName}/${this.codebaseConfiguration.name}`,
            imageTagMutability: 'MUTABLE',
            imageScanningConfiguration: {
                scanOnPush: true,
            },
            lifecyclePolicy: {
                lifecyclePolicyText: JSON.stringify({
                    rules: [
                        {
                            rulePriority: 1,
                            description: "Delete untagged images after 7 days",
                            selection: {
                                tagStatus: "untagged",
                                countType: "sinceImagePushed",
                                countUnit: "days",
                                countNumber: 7,
                            },
                            action: {
                                type: "expire"
                            },
                        },
                    ],
                }),
            },
            repositoryPolicyText: this.pipelinesFile.accounts ? {
                Statement: [
                    {
                        Effect: "Allow",
                        Principal: {
                            AWS: this.pipelinesFile.accounts?.map(a => `arn:aws:iam::${a}:root`) || [],
                        },
                        Action: [
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:CompleteLayerUpload",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:InitiateLayerUpload",
                            "ecr:PutImage",
                            "ecr:UploadLayerPart"
                        ]
                    }
                ]
            } : undefined,
        });
    }

    private updatePipelineBuildProject() {
        const buildProject = this.template.getResource("BuildProject") as cdk.aws_codebuild.CfnProject;

        const currentEnvironment = buildProject.environment as cdk.aws_codebuild.CfnProject.EnvironmentProperty;
        const currentEnvironmentVariables = currentEnvironment.environmentVariables as Array<cdk.aws_codebuild.CfnProject.EnvironmentVariableProperty>;
        const deployEnvironmentVariables = [
            ...currentEnvironmentVariables,
            {
                name: 'CODESTAR_CONNECTION_ID',
                value: this.codestarConnection.id
            },
            {
                name: 'DEPLOY_REPOSITORY',
                value: this.deployRepository
            },
            {
                name: 'CODEBASE_REPOSITORY',
                value: this.codebaseConfiguration.repository
            },
            {
                name: 'COPILOT_SERVICES',
                value: this.codebaseConfiguration.services.join(' ')
            },
            {
                name: 'ECR_REPOSITORY',
                value: this.ecrRepository()
            },
        ];

        if (this.codebaseConfiguration.deploy_repository_branch){
            deployEnvironmentVariables.push({name: 'DEPLOY_REPOSITORY_BRANCH', value: this.codebaseConfiguration.deploy_repository_branch})
        }

        buildProject.environment = {
            ...buildProject.environment,
            image: 'public.ecr.aws/uktrade/ci-image-builder:tag-latest',
            environmentVariables: deployEnvironmentVariables
        } as cdk.aws_codebuild.CfnProject.EnvironmentProperty;

        const currentSource = buildProject.source as cdk.aws_codebuild.CfnProject.SourceProperty;

        buildProject.source = {
            ...currentSource,
            buildSpec: stringify(parse(
                readFileSync(path.join(__dirname, 'buildspec.deploy.yml')).toString('utf-8'),
            )),
        };
    }

    private updatePipelines() {
        const existingPipeline = this.template.getResource("Pipeline") as cdk.aws_codepipeline.CfnPipeline;

        // Here we co-opt the existing pipeline resource to alter covering our first pipeline.
        const [firstPipelineConfiguration] = this.codebaseConfiguration.pipelines.splice(0, 1);
        this.updateExistingPipeline(existingPipeline, firstPipelineConfiguration);

        for (const [index, pipelineConfiguration] of this.codebaseConfiguration.pipelines.entries()) {
            this.createPipeline(index, pipelineConfiguration, existingPipeline);
        }
    }

    private ecrRepository(){
        return cdk.Fn.ref('ECRRepository');
    }

    private additionalEcrRepository(){
        return this.codebaseConfiguration.additional_ecr_repository || "";
    }

    private createPipeline(index: number, pipelineConfig: PipelinesConfiguration['codebase_pipelines'][0]['pipelines'][0], existingPipeline: cdk.aws_codepipeline.CfnPipeline) {
        const pipeline = new cdk.aws_codepipeline.CfnPipeline(this, `Pipeline${index + 1}`, {
            name: `pipeline-${this.appName}-${this.codebaseConfiguration.name}-${pipelineConfig.name}`,
            roleArn: cdk.Fn.getAtt('PipelineRole', 'Arn').toString(),
            artifactStores: existingPipeline.artifactStores,
            stages: [
                {
                    name: "Source",
                    actions: [
                        {
                            name: 'ImagePublished',
                            runOrder: 1,
                            configuration: {
                                RepositoryName: this.ecrRepository(),
                                ImageTag: pipelineConfig.tag ? 'tag-latest' : `branch-${pipelineConfig.branch?.replace(/\//gi, '-')}`,
                            },
                            outputArtifacts: [{name: 'ECRMetadata'}],
                            actionTypeId: {
                                category: 'Source',
                                owner: 'AWS',
                                version: '1',
                                provider: 'ECR',
                            },
                        },
                    ],
                },
            ],
        });

        this.addPipelineStages(pipelineConfig, pipeline);
        this.createEventRule(pipeline, pipelineConfig, (index + 1).toString());
    }

    private updateExistingPipeline(pipeline: cdk.aws_codepipeline.CfnPipeline, pipelineConfig: typeof this.codebaseConfiguration['pipelines'][0]) {
        // Update the pipeline name
        pipeline.name = `pipeline-${this.appName}-${this.codebaseConfiguration.name}-${pipelineConfig.name}`;

        // Replace source code action trigger with ECR push
        pipeline.stages[0].actions[0] = {
            name: 'ImagePublished',
            runOrder: 1,
            configuration: {
                RepositoryName: this.ecrRepository(),
                ImageTag: pipelineConfig.tag ? 'tag-latest' : `branch-${pipelineConfig.branch}`,
            },
            outputArtifacts: [{name: 'ECRMetadata'}],
            actionTypeId: {
                category: 'Source',
                owner: 'AWS',
                version: '1',
                provider: 'ECR',
            },
        };

        // Remove all other stages
        (pipeline.stages as Array<unknown>).splice(1, (pipeline.stages as Array<unknown>).length - 1);

        this.addPipelineStages(pipelineConfig, pipeline);
        this.createEventRule(pipeline, pipelineConfig);
    }

    private addPipelineStages(pipelineConfig: typeof this.codebaseConfiguration['pipelines'][0], pipeline: cdk.aws_codepipeline.CfnPipeline) {
        for (const environment of pipelineConfig.environments) {
            const environmentStage: {
                name: string;
                actions: Array<cdk.aws_codepipeline.CfnPipeline.ActionDeclarationProperty>;
            } = {name: `DeployTo-${environment.name}`, actions: []};

            if (environment.requires_approval) {
                environmentStage.actions.push({
                    actionTypeId: {
                        category: "Approval",
                        owner: "AWS",
                        provider: "Manual",
                        version: "1"
                    },
                    name: `ApprovePromotionTo-${environment.name}`,
                    runOrder: 1
                });
            }

            environmentStage.actions.push({
                name: 'Deploy',
                runOrder: environment.requires_approval ? 2 : 1,
                inputArtifacts: [
                    {name: 'ECRMetadata'},
                ],
                actionTypeId: {
                    category: 'Build',
                    owner: 'AWS',
                    version: '1',
                    provider: 'CodeBuild',
                },
                configuration: {
                    ProjectName: cdk.Fn.ref('BuildProject'),
                    PrimarySource: 'ECRMetadata',
                    EnvironmentVariables: JSON.stringify([
                        {name: 'COPILOT_ENVIRONMENT', value: environment.name},
                        {
                            name: 'ECR_TAG_PATTERN',
                            value: pipelineConfig.tag ? 'tag-latest' : `branch-${pipelineConfig.branch}`
                        },
                    ]),
                },
            });

            (pipeline.stages as Array<cdk.aws_codepipeline.CfnPipeline.StageDeclarationProperty>).push(environmentStage);
        }
    }

    private createEventRuleRole() {
        new cdk.aws_iam.CfnRole(this, 'EventRole', {
            roleName: `${this.appName}-${this.codebaseConfiguration.name}-pipeline-trigger-role`,
            assumeRolePolicyDocument: {
                Statement: [{
                    Effect: "Allow",
                    Principal: {
                        Service: "events.amazonaws.com"
                    },
                    Action: "sts:AssumeRole"
                }],
            },
            policies: [{
                policyName: `${this.appName}-${this.codebaseConfiguration.name}-pipeline-trigger-policy`,
                policyDocument: {
                    Statement: [{
                        Effect: 'Allow',
                        Action: ["codepipeline:StartPipelineExecution"],
                        Resource: ["*"],
                    }],
                }
            }]
        });
    }

    private createEventRule(pipeline: cdk.aws_codepipeline.CfnPipeline, pipelineConfig: PipelinesConfiguration['codebase_pipelines'][0]['pipelines'][0], suffix: string = '') {
        const watchImageTag = pipelineConfig.tag ? 'tag-latest' : `branch-${pipelineConfig.branch}`;
        const ecrRepository = `${this.appName}/${this.codebaseConfiguration.name}`;
        new cdk.aws_events.CfnRule(this, `EventRule${suffix}`, {
            name: `trigger-${pipeline.name}`,
            description: `Trigger the ${pipeline.name} pipeline when a tag called '${watchImageTag}' is pushed to the repo '${ecrRepository}'`,
            eventPattern: {
                source: ["aws.ecr"],
                detail: {
                    'action-type': ["PUSH"],
                    'image-tag': [watchImageTag],
                    'repository-name': [ecrRepository],
                    result: ["SUCCESS"],
                },
            },
            targets: [{
                id: `${pipeline.name}`,
                arn: `arn:aws:codepipeline:${this.region}:${this.account}:${pipeline.name}`,
                roleArn: cdk.Fn.getAtt('EventRole', 'Arn').toString(),
            }]
        });
    }

    private allowBuildProjectToUseCodestarConnection() {
        const buildProjectPolicy = this.template.getResource("BuildProjectPolicy") as cdk.aws_iam.CfnPolicy;
        (buildProjectPolicy.policyDocument.Statement as Array<any>).push({
            Effect: 'Allow',
            Action: [
                'codestar-connections:GetConnectionToken',
                'codestar-connections:UseConnection',
            ],
            Resource: [this.codestarConnection.arn],
        });
    }

    private allowPipelineToUseEnvManagerRole() {
        const pipelineRolePolicy = this.template.getResource("PipelineRolePolicy") as cdk.aws_iam.CfnPolicy;
        (pipelineRolePolicy.policyDocument.Statement as Array<any>).push(
            this.getEnvManagerRolePolicyDoc()
        );
    }

    private allowBuildProjectToUseEnvManagerRole() {
        const buildProjectPolicy = this.template.getResource("BuildProjectPolicy") as cdk.aws_iam.CfnPolicy;
        (buildProjectPolicy.policyDocument.Statement as Array<any>).push(
            this.getEnvManagerRolePolicyDoc()
        );
        (buildProjectPolicy.policyDocument.Statement as Array<any>).push(
            this.addECRBatchDeleteToBuildProjectRolePolicyDoc()
        );
    }

    private getEnvManagerRolePolicyDoc() {
        return {
            Effect: 'Allow',
            Action: ['sts:AssumeRole'],
            Resource: [`arn:aws:iam::${this.account}:role/${this.appName}-*-EnvManagerRole`],
        };
    }

    private addECRBatchDeleteToBuildProjectRolePolicyDoc() {
        return {
            Effect: 'Allow',
            Action: ['ecr:BatchDeleteImage'],
            Resource: ['*'],
        };
    }

    private allowPipelineToDescribeECRImages() {
        const pipelineRolePolicy = this.template.getResource("PipelineRolePolicy") as cdk.aws_iam.CfnPolicy;
        pipelineRolePolicy.policyDocument.Statement[0].Action.push('ecr:DescribeImages');
    }

    private loadManifestFiles() {
        const pipelineRoot = path.join(process.cwd(), '..');
        const deployRepoRoot = path.join(pipelineRoot, '..', '..', '..');

        // Load copilot pipeline manifest
        this.pipelineManifest = parse(readFileSync(
            path.join(pipelineRoot, 'manifest.yml'),
        ).toString('utf-8')) as PipelineManifest;

        // Load dbt-platform-helper pipelines configurations
        this.pipelinesFile = parse(readFileSync(
            path.join(deployRepoRoot, 'platform-config.yml'),
        ).toString('utf-8')) as PipelinesConfiguration;

        this.codebaseConfiguration = this.getFullCodebaseConfiguration();
    }

    private getFullCodebaseConfiguration() {
        const pipelineRoot = path.join(process.cwd(), '..');
        const deployRepoRoot = path.join(pipelineRoot, '..', '..', '..');
        const pipelinesFile = parse(readFileSync(
            path.join(deployRepoRoot, 'platform-config.yml'),
        ).toString('utf-8')) as PipelinesConfiguration;

        const codebaseConfiguration = pipelinesFile.codebase_pipelines.find(c => c.name === this.pipelineManifest.name);

        if (!codebaseConfiguration) {
            throw new Error(`Could not find a codebase configuration for ${this.pipelineManifest.name}, ensure ./platform-config.yml is up to date`);
        }

        return codebaseConfiguration
    }

    private loadCodestarConnection() {
        const codestarConnections = JSON.parse(execSync('aws codestar-connections list-connections').toString('utf-8')) as CodeStarConnectionListConnectionsOutput;
        const codestarConnectionArn = codestarConnections.Connections
            .find(c => c.ConnectionName === this.pipelineManifest.source.properties.connection_name)?.ConnectionArn;

        const codestarConnectionId = codestarConnectionArn?.split('/').pop();

        if (!codestarConnectionArn || !codestarConnectionId) {
            throw new Error(`Could not find a codestar connection called ${this.pipelineManifest.source.properties.connection_name}, have you created it?`);
        }

        this.codestarConnection = {arn: codestarConnectionArn, id: codestarConnectionId};
    }

    private loadGitRemote() {
        const output = execSync('git remote get-url origin').toString('utf-8');

        if (!output.startsWith('git@')) throw new URIError("Git remote is not an SSH URL.");

        const deployRepository = output.split(':').pop()?.replace('.git', '').replace('\n', '');

        if (!deployRepository) throw new Error("Could not find Git remote.");

        this.deployRepository = deployRepository;
    }

    private uploadPipelineConfiguration() {
        new cdk.aws_ssm.CfnParameter(this, 'CodebaseConfiguration', {
            name: `/copilot/applications/${this.appName}/codebases/${this.codebaseConfiguration.name}`,
            type: "String",
            value: JSON.stringify(this.getFullCodebaseConfiguration()),
        });
    }
}
