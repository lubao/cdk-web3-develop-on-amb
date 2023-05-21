import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_cloud9 as cloud9,
    aws_managedblockchain as amb,
    aws_codecommit as codecommit,
    # aws_sqs as sqs,
)
from constructs import Construct
# import os


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
        # Code commit
        # TODO Add NFT Labs source code...
        # _nft_repo = codecommit.Repository(self, "NFTLabCodeCommit",
        #     repository_name="NFTLab",
        #     code=codecommit.Code.from_directory('src')
        # )
        
        # ISSUE: Need a way ot share Cloud9 Environment to other
        # Otherwise, user cannot view it on the console...
        # Create cloud9 Develope Environment
        # Cloud9-alpha will create EC2 and not showed on Cloud9 Console.
        # _cloud9_env = cloud9.CfnEnvironmentEC2(
        #     self, 'NFTLabCloud9',
        #     instance_type='t3.large',
        #     image_id='ubuntu-18.04-x86_64',
        #     repositories=[cloud9.CfnEnvironmentEC2.RepositoryProperty(
        #         path_component='/NFTLabs',
        #         repository_url=_nft_repo.repository_clone_url_http
        #     )],
        # )
        
        
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
                # cpu_architecture=ecs.CpuArchitecture.ARM64
            ),
        )
        
        # Add IPFS kubo container v0.20.0 to task
        # By default, Amazon ECS tasks that are hosted on 
        # Fargate using platform version 1.4.0 or later receive a 
        # minimum of 20 GiB of ephemeral storage
        _kubo_container = _ipfs_task.add_container(
            'IpfsKuboNode',
            image=ecs.ContainerImage.from_registry(
                'ipfs/kubo'
            ),
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
        
        # Secruity Group for IPFS Fargate Services
        _ipfs_srv_sg = ec2.SecurityGroup(self, 'IpfsServiceSecurityGroup',
                                         vpc=_vpc,
                                         description='Allow access to IPFS nodes'
                                         )

        _ipfs_srv_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(4001),
            description='IPFS swarm port open to the Internet'
        )

        # _ipfs_srv_sg.add_ingress_rule(
        #     peer=ec2.Peer.ipv4(_vpc.vpc_cidr_block),
        #     connection=ec2.Port.tcp(9096),
        #     description='IPFS Cluster Swarm from internal network only'
        # )

        _ipfs_srv_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(_vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5001),
            description='IPFS RPC API from internal network only'
        )

        # Create ECS Fargate Service
        _ipfs_srv = ecs.FargateService(
            self, 'IpfsSrv',
            cluster=_ecs_cluster,
            task_definition=_ipfs_task,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(
                availability_zones=[_vpc.availability_zones[0]],
                one_per_az=False,
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_groups=[_ipfs_srv_sg],
            enable_execute_command=True,
            max_healthy_percent=100,
            min_healthy_percent=0
        )


        
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
        cdk.CfnOutput(
            self, 'GoerliNodeWSEndpoint',
            value=f'wss://{_goerli_node.attr_node_id}.wss.t.'
            f'ethereum.managedblockchain.{self.region}.amazonaws.com?'
            f'billingtoken={_billing_token.attr_billing_token}',
            description='Endpoint for Managed Blockchain Goerli Node',
        )
        
        # TODO IPFS Endpoint

