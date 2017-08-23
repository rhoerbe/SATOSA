#!/usr/bin/env bash

main() {
    get_commandline_opts "$@"
    set_openssl_config
    create_keypair_and_certificate
    show_result
}


get_commandline_opts() {
    basicConstraintsCA='FALSE'
    keysize=2048
    x509subject='/C=AT/ST=Wien/L=Wien/O=BKA/OU=IT/CN=SATOSA'
    keyname='metadata'
    while getopts ":ck:n:s:v" opt; do
      case $opt in
        c) basicConstraintsCA='TRUE';;
        k) keysize=$OPTARG
           re='^[0-9]{3,5}$'
           if ! [[ $OPTARG =~ $re ]] ; then
              echo "error: -k argument is not a number in the range from 1024 .. 16384" >&2; exit 1
           fi;;
        n) keyname=$OPTARG;;
        v) verbose="True";;
        s) x509subject=$OPTARG;;
        :) echo "Option -$OPTARG requires an argument"; exit 1;;
        *) usage; exit 0;;
      esac
    done
    #shift $((OPTIND-1))
}


usage() {
    cat << EOF
        Usage: $0 [-k <NNNN>] [-n <key name>] [-v] [-s <X509 subject>]
          -c  Use certificate as CA (basicConstraints:CA=TRUE)
          -h  print this help text
          -k  keysize (default: $keysize)
          -n  file name of key and certificate (default: $keyname)
          -v  verbose
          -s  x509 subject DN (default: $x509subject)

        Example:
           $0 -v -s "/C=AT/ST=Wien/L=Wien/O=BKA/OU=IT/CN=SATOSA" -n satosa
EOF
}


set_openssl_config() {
    cat > /tmp/openssl.cfg <<EOT
[req]
distinguished_name=dn
[ dn ]
[ ext ]
basicConstraints=CA:$basicConstraintsCA
EOT

}


create_keypair_and_certificate() {
    cmd1="openssl req
        -config /tmp/openssl.cfg
        -x509 -newkey rsa:${keysize}
        -keyout ./${keyname}_key_pkcs8.pem
        -out ./${keyname}.crt
        -sha256 -days 3650 -nodes
        -batch -subj \"$x509subject\"
    "
    cmd2="openssl rsa -in ./${keyname}_key_pkcs8.pem -out ./${keyname}.key"

    if [ "$verbose" == "True" ]; then
        echo $cmd1
        echo $cmd2
    fi

    tmpname=/tmp/$(basename $0.tmp)
    echo $cmd1 > $tmpname   # indirect execution as workaround against "invalid subject not beginning with '/'"
    bash $tmpname
    $cmd2
    chmod 600 ./${keyname}.key
}


show_result() {
    ls -l .
}


main "$@"