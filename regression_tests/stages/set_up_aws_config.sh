#!/bin/bash

configure_aws_profile() {
  local profile_name=$1
  local access_key_id=$2
  local secret_access_key=$3
  local session_token_key=$4

  echo -e "\nConfigure $profile_name AWS Profile"
  # populates the ~/.aws/credentials file
  aws configure set aws_access_key_id "$access_key_id" --profile "$profile_name"
  aws configure set aws_secret_access_key "$secret_access_key" --profile "$profile_name"
  aws configure set aws_session_token "$session_token_key" --profile "$profile_name"

  # populates the ~/.aws/config file
  aws configure set region "eu-west-2" --profile "$profile_name"
  aws configure set output "json" --profile "$profile_name"
}

echo -e "\nConfigure platform-sandbox profile"
configure_aws_profile "platform-sandbox" "$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID" "$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY" "$PLATFORM_SANDBOX_AWS_SESSION_TOKEN"
