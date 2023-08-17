echo "Welcome to the client container for opensearch services."
echo

trap quit_shell INT

function quit_shell() {
  echo
  echo "Exiting..."
  exit
}

function os_entry() {
  while true; do
    os_run_next_command
  done
}

function os_run_next_command() {
  echo -n "opensearch => "
  read
  echo "Running opensearch-cli $REPLY"
  /usr/share/opensearch/opensearch-cli $REPLY --profile connection
}

os_entry
quit_shell
