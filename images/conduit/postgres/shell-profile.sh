

psql "$(echo $DB_SECRET | jq -rc '"postgres://\(.username):\(.password)@\(.host):\(.port)/\(.dbname)"')"

kill `ps -e -o pid,comm | grep 'tail' | awk '{print$1}'`
