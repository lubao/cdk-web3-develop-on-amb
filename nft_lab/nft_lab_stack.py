import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_cloud9_alpha as cloud9,
    aws_managedblockchain as amb,
    # aws_sqs as sqs,
)
from constructs import Construct


class NftLabStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Create A VPC with 3 public subnet
        _vpc = ec2.Vpc(
            self, "NFTLabs",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name='public',
                    subnet_type=ec2.SubnetType.PUBLIC
                )
            ],
            max_azs=3
        )
        
        # Create cloud9 Develope Environment
        # Cloud9-alpha will create EC2 and not showed on Cloud9 Console.
        # TODO
        # TODO Code commit
        
        # Create ECS Cluster for IPFS node
        _ecs_cluster = ecs.Cluster(self, "IpfsEcsCluster", vpc=_vpc)
        
        # Create IPFS kubo Fargate Task
        _ipfs_task = ecs.FargateTaskDefinition(
            self, 'IpfsKuboTask',
            # compatibility=ecs.Compatibility.FARGATE,
            cpu=1024,
            memory_limit_mib=2048,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64
            ),
        )
        
        # Add IPFS kubo container to task
        # By default, Amazon ECS tasks that are hosted on 
        # Fargate using platform version 1.4.0 or later receive a 
        # minimum of 20 GiB of ephemeral storage
        _kubo_container = _ipfs_task.add_container(
            'IpfsKuboNode',
            image=ecs.ContainerImage.from_registry('ipfs/kubo:latest'),
            port_mappings=[
                ecs.PortMapping(container_port=4001),
                ecs.PortMapping(container_port=5001),
                ecs.PortMapping(container_port=8080),
            ],
            health_check=ecs.HealthCheck(
                command=['/usr/local/bin/ipfs dag stat '
                         '/ipfs/QmUNLLsPACCz1vLxQVkXqqLX5R1X345qqfHbsf67hvA3Nn'
                         ' || exit 1 ']
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix='IpfsKuboNode'
            )
        )
        
        # TODO create ECS service for ipfs task
        
        # Create BILLING_TOKEN for Amazon Managed Blockchain
        _billing_token = amb.CfnAccessor(self, "billing_token",
            accessor_type="BILLING_TOKEN",
        )
        
        # Create AMB Goerli Node
        _goerli_node = amb.CfnNode(self, "GoerliNode",
            network_id="n-ethereum-goerli",
            node_configuration=amb.CfnNode.NodeConfigurationProperty(
                availability_zone=_vpc.availability_zones[0],
                instance_type="bc.t3.large"
            ),
        )
        
        # Output
        cdk.CfnOutput(
            self, 'GoerliNodeEndpoint',
            value=f'https://{_goerli_node.attr_node_id}.t.'
            f'ethereum.managedblockchain.{self.region}.amazonaws.com?'
            f'billingtoken={_billing_token.attr_billing_token}',
            description='Endpoint for Managed Blockchain Goerli Node',
        )
        
        # TODO IPFS Endpoint

