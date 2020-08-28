#!/bin/bash

CHAIN=$1

# Use "${<variable>,,}" to convert the CHAIN variable to lower case
# Reference: https://stackoverflow.com/a/2264537 
case "${CHAIN,,}" in
    "btc")
        PORT="9002"
        ;;

    "ltc")
        PORT="9003"
        ;;

    # Print the help command
    "")
        ;&
    
    "help")
        exec boltzcli help
        exit 0
        ;;

    *)
        echo "Chain $CHAIN not supported"
        exit 1
        ;;
esac

exec boltzcli --port $PORT ${@:2}
