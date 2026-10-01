# output "sqs_queue" {
#   value = {
#     for k, queue in aws_sqs_queue.this :
#     k => {
#       arn  = queue.arn
#       id   = queue.id
#       name = queue.name
#     }
#   }
# }

# output "id" {
#   description = "SQS queue URL."
#   value       = aws_sqs_queue.this.id
# }

# output "arn" {
#   description = "SQS queue ARN."
#   value       = aws_sqs_queue.this.arn
# }

# output "name" {
#   description = "SQS queue name."
#   value       = aws_sqs_queue.this.name
# }

# output "dlq_arn" {
#   description = "DLQ ARN."
#   value       = try(aws_sqs_queue.dlq[0].arn, null)
# }