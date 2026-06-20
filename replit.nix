{pkgs}: {
  deps = [
    pkgs.memcached
    pkgs.curl
    pkgs.openssl
    pkgs.pkg-config
    pkgs.libpq
    pkgs.postgresql
  ];
}
