#!/bin/bash

set -e

echo "\n******************************************************************"
echo "* Running platform-helper conduit for POSTGRES with READ access *"
echo "******************************************************************\n\n\n"

expect << EOD
  # Timeout is set to 120 to copilot to check infrastructure, and allow the container to boot 
  set timeout 120
  global spawn_id timeout
  spawn platform-helper conduit demodjango-postgres --app demodjango --env ${TARGET_ENVIRONMENT} --access read
  expect {
    "main=> " {
      send "SELECT 1;\r"
      expect {
        "(1 row)" {

	  send "quit\r"
	  exit 0
	}
      }
    }
  }
  send_user "*************************************************************************\n"
  send_user "* FAILED: Running platform-helper conduit for POSTGRES with READ access *\n"
  send_user "*************************************************************************"
  exit 1
EOD

echo "\n******************************************************************"
echo "* SUCCESS: platform-helper conduit for POSTGRES with READ access *"
echo "******************************************************************\n\n\n"
echo "**********************************************************************************"
echo "* Running platform-helper conduit for POSTGRES with READ - Write Permission Test *"
echo "**********************************************************************************\n"

expect  << EOD
  # Timeout is set to 120 to copilot to check infrastructure, and allow the container to boot 
  set timeout 120
  global spawn_id timeout
  spawn platform-helper conduit demodjango-postgres --app demodjango --env ${TARGET_ENVIRONMENT} --access read
  expect {
    "main=> " {
      send "CREATE TABLE regression_test (test VARCHAR(10));\r"
      expect {
        "permission denied" {
          exit 0
        }
      } 
	  send "quit\r"
    }
  }
  send_user "*************************************************************************************************\n"
  send_user "* FAILED: Running platform-helper conduit for POSTGRES with READ access - Write Permission Test *\n"
  send_user "*************************************************************************************************"
  exit 1
EOD

echo "\n******************************************************************"
echo "* SUCCESS: platform-helper conduit for POSTGRES with READ access *"
echo "******************************************************************\n\n\n"
echo "******************************************************************"
echo "* Running platform-helper conduit for POSTGRES with WRITE access *"
echo "******************************************************************\n"

expect  << EOD
  # Timeout is set to 120 to copilot to check infrastructure, and allow the container to boot 
  set timeout 120
  global spawn_id timeout
  spawn platform-helper conduit demodjango-postgres --app demodjango --env ${TARGET_ENVIRONMENT} --access write
  expect {
    "main=> " {
      send "CREATE TABLE regression_test (test VARCHAR(10));\r"
      expect {
        "permission denied" {
          exit 1
        }
        "CREATE TABLE"  {
          send "DROP table regression_test;\r" 
          exit 0;
        }
      } 
	  send "quit\r"
    }
  }
  send_user "**************************************************************************\n"
  send_user "* FAILED: Running platform-helper conduit for POSTGRES with WRITE access *\n"
  send_user "**************************************************************************"
  exit 1
EOD

echo "******************************************************************"
echo "* SUCCESS: platform-helper conduit for POSTGRES with WRITE access *"
echo "******************************************************************\n\n\n"
echo "******************************************************************"
echo "* Running platform-helper conduit for POSTGRES with ADMIN access *"
echo "******************************************************************\n"

expect  << EOD
  # Timeout is set to 120 to copilot to check infrastructure, and allow the container to boot 
  set timeout 120
  global spawn_id timeout
  spawn platform-helper conduit demodjango-postgres --app demodjango --env ${TARGET_ENVIRONMENT} --access admin
  expect {
    "main=> " {
      send "CREATE DATABASE regression_test;\r"
      expect {
        "permission denied" {
          send_user "*************************************************************************************************\n"
          send_user "* FAILED: Creating Database when running platform-helper conduit for POSTGRES with ADMIN access *\n"
          send_user "*************************************************************************************************"
          exit 1
        }
        "CREATE DATABASE"  {
          send "DROP DATABASE regression_test;\r" 
          exit 0;
        }
      } 
	  send "quit\r"
    }
  }
  send_user "**************************************************************************\n"
  send_user "* FAILED: Running platform-helper conduit for POSTGRES with ADMIN access *\n"
  send_user "**************************************************************************"
  exit 1
EOD

echo "\n******************************************************************\n"
echo "* SUCCESS: platform-helper conduit for POSTGRES with ADMIN access *\n"
echo "******************************************************************\n\n\n"
echo "\n*********************************************\n"
echo "* Running platform-helper conduit for REDIS *\n"
echo "*********************************************\n"

expect << EOD
  set timeout 120
  set force_conservative 1
  global spawn_id timeout
  spawn platform-helper conduit demodjango-redis --app demodjango --env ${TARGET_ENVIRONMENT}
  expect {
    "Welcome to the client container for redis services." {
    sleep 50
    send "exit\r"
    exit 0
	  }
  }
  send_user "*****************************************************\n"
  send_user "* FAILED: Running platform-helper conduit for REDIS *\n"
  send_user "*****************************************************"
  exit 1
EOD

echo "\n*********************************************"
echo "* SUCCESS: platform-helper conduit for REDIS *"
echo "*********************************************\n\n\n"


echo "\n**************************************************"
echo "* Running platform-helper conduit for OPENSEARCH *"
echo "**************************************************\n"

expect << EOD
  set timeout 120
  global spawn_id timeout
  spawn platform-helper conduit demodjango-opensearch --app demodjango --env ${TARGET_ENVIRONMENT}
  expect {
    "opensearch =>" {
    exit 0
	  }
  }
  send_user "****************************************************************************\n"
  send_user "* FAILED: Running platform-helper conduit for OPENSEARCH with ADMIN access *\n"
  send_user "****************************************************************************"
  exit 1
EOD
echo "\n**************************************************"
echo "* SUCCESS: platform-helper conduit for OPENSEARCH *"
echo "**************************************************\n"