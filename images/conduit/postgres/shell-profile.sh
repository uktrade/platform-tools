echo "Welcome to the client container for postgres services."
echo $CONNECTION_SECRET | jq -rc '"Connecting to database \"\(.dbname)\" on \"\(.host)\""'
echo

psql "$(echo $CONNECTION_SECRET | jq -rc '"postgres://\(.username):\(.password)@\(.host):\(.port)/\(.dbname)"')"

exit
