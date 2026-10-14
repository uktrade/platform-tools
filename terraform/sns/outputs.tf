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
