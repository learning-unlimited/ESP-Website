#!/bin/sh
exec ssh -o NoHostAuthenticationForLocalhost=yes -i ../keys/id_rsa "$@"
