# In order to support the --dns-interface option in curl, we need to use the c-ares library with --enable-ares option

# Here we describe <how to enable>/<how to disable>/<what are dependencies>
PACKAGECONFIG[c-ares] = "--enable-ares,--disable-ares,c-ares"

# Here we add the c-ares option to the original recipe options
PACKAGECONFIG += "${@bb.utils.contains("DISTRO_FEATURES", "ipv6", "ipv6", "", d)} gnutls proxy zlib c-ares"

