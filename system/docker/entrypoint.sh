#! /bin/bash

# Setting the user/group id's of the slowuser
# If the id's are not given through the environmental variables,
# extract them from the /project directory.

# Do this only when the user in the container is "root" (e.g., in Docker)
if [ $(whoami) != 'root' ]; then
    exec "$@"
fi

if [ -z "$USER_ID" ]; then
    USER_ID=$(ls -dln /project | cut --delimiter=' ' --field=3)
fi    
if [ $USER_ID != 0 ]; then
   usermod -u $USER_ID slowuser
fi
if [ -z "$GROUP_ID" ]; then
    GROUP_ID=$(ls -dln /project | cut --delimiter=' ' --field=4)
fi
if [ $GROUP_ID != 0 ]; then
   groupmod -g $GROUP_ID slowuser
fi

exec gosu slowuser "$@"
