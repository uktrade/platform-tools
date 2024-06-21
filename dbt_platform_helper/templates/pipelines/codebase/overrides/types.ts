import * as cdk from "aws-cdk-lib";

export interface TransformedStackProps extends cdk.StackProps {
    readonly appName: string;
}

export interface PipelineManifest {
    name: string;
    version: 1;
    source: {
        provider: 'GitHub';
        properties: {
            branch: string;
            repository: string;
            connection_name: string;
        };
    };
    stages: Array<{
        name: string;
        requires_approval?: boolean;
    }>;
}

export interface PipelinesConfiguration {
    accounts?: Array<string>;
    codebase_pipelines: Array<{
        name: string;
        repository: string;
        additional_ecr_repository?: string;
        services: Array<string>;
        pipelines: Array<{
            name: string;
            branch?: string;
            tag?: boolean;
            environments: Array<{
                name: string;
                requires_approval?: boolean;
            }>;
        }>;
    }>;
}

export interface CodeStarConnectionListConnectionsOutput {
    Connections: Array<{
        ConnectionName: string;
        ConnectionArn: string;
        ProviderType: string;
        OwnerAccountId: string;
        ConnectionStatus: string;
    }>;
}
