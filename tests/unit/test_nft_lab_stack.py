import aws_cdk as core
import aws_cdk.assertions as assertions

from nft_lab.nft_lab_stack import NftLabStack

# example tests. To run these tests, uncomment this file along with the example
# resource in nft_lab/nft_lab_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = NftLabStack(app, "nft-lab")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
