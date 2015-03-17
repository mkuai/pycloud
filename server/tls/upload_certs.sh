#!/bin/bash

CLOUDLET_HOST=$1
CLOUDLET_USER=$2
REMOTE_PATH=$3

scp -r ./certs/ $CLOUDLET_USER@$CLOUDLET_HOST:$REMOTE_PATH
scp deploy_certs.sh $CLOUDLET_USER@$CLOUDLET_HOST:$REMOTE_PATH
