echo "Welcome to the client container for postgres services."

if [[ "$IS_POSTGRES_ADMIN_TASK" == "True" ]]; then
    echo "Connecting to database \"${DB_NAME}\" on host \"${HOST}\""
    psql "postgres://${USERNAME}:${PASSWORD}@${HOST}:${PORT}/${DB_NAME}"
else
    echo $CONNECTION_SECRET | jq -rc '"Connecting to database \"\(.dbname)\" on host \"\(.host)\""'
    psql "$(echo $CONNECTION_SECRET | jq -rc '"postgres://\(.username):\(.password)@\(.host):\(.port)/\(.dbname)"')"
fi

exit
