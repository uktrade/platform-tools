output "topic_arn" {
  value = aws_sns_topic.this.arn
}

output "queue_arn" {
  value = aws_sqs_queue.this.arn
}