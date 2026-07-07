#!/bin/bash
# TODO: Replace this fragile grep check with a runtime check in @verify_permission
# itself that raises an error at import time if applied in the wrong decorator order.

DIR=$1

if [ -d "$DIR" ] # check if the path $DIR exists
then
  if grep -PHaoz -q  '@verify_permission.*\n.*\.route' -R $DIR # check if any matches for missordered decorators are found
  then
    echo "Error: The following permission decorators are out of order";
    grep -PHaozn  '@verify_permission.*\n.*\.route' -R $DIR # print all matches
    exit 1
  else
    echo "Success: OK! All @verify_permission decorators are in order!"
    exit 0
  fi
else
    echo "Error: $DIR cannot be found, make sure to pass the correct path"; exit 1;
fi
