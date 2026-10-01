output "topics" {
  value = {
    for topic_name, sns_topic in aws_sns_topic.this :
    topic_name => {
      arn  = sns_topic.arn
      id   = sns_topic.id
      name = sns_topic.name
    }
  }
}


# output "topic_arn" {
#   description = "ARN of the SNS topic."
#   value       = aws_sns_topic.this.arn
# }

# output "topic_arn" {
#   value = {
#     for topic_name, sns_topic in aws_sns_topic.this :
#     topic_name => sns_topic.arn
#   }
# }

# output "topic_name" {
#   value = {
#     for topic_name, sns_topic in aws_sns_topic.this :
#     topic_name => sns_topic.name
#   }
# }

# output "topic_id" {
#   description = "ID of the SNS topic."
#   value       = aws_sns_topic.this.name
# }