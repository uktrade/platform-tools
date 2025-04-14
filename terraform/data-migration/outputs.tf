# output needed for the s3 tests asserting creation of submodule (asserting creation directly results in a failure during the codebuild job)
output "module_exists" {
  value = true
}

output "sources" {
  value = var.sources
}
