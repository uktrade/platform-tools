echo "Welcome to the client container for postgres services."
echo $DB_SECRET | jq -rc '"Connecting to database \"\(.dbname)\" on \"\(.host)\""'
echo

psql "$(echo $DB_SECRET | jq -rc '"postgres://\(.username):\(.password)@\(.host):\(.port)/\(.dbname)"')"

if [[ `ps -e -o pid,comm | grep 'psql' | wc -l` == "0" ]]; then
  kill `ps -e -o pid,comm | grep 'tail' | awk '{print$1}'`
fi

exit
