echo "Welcome to the client container for redis services."
echo

redis-cli -u $CONNECTION_SECRET

if [[ `ps -e -o pid,comm | grep 'redis-cli' | wc -l` == "0" ]]; then
  kill `ps -e -o pid,comm | grep 'tail' | awk '{print$1}'`
fi

exit
