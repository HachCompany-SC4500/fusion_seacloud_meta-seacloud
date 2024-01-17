# This is a fix to be able to include watchdog-keepalive in the image and to
# have a working SDK.
#
# Original problem:
# During SDK generation, Yocto get the list of installed packages and tries to
# add the corresponding *-dev packages to the SDK. As there is no
# watchdog-keepalive-dev package, Yocto uses watchdog-dev package as a fallback
# (see oe-pkgdata-util). watchdog-dev RDEPENDS on watchdog package, so Yocto
# also includes watchdog package in the SDK. As watchdog and watchdog-keepalive
# packages are flags as conflicting (RCONFLICTS in the original recipe), the
# SDK generation fails. The failure just reports a warning but at the end a lot
# of things seems to be missing in the SDK (debug packages, dns_sd header ...)
#
# Fix: 
# We add the watchdog-keepalive-dev package. The package will be empty (as
# watchdog-dev in fact) but that will avoid that watchdog-dev is installed in
# the SDK.
PACKAGES += " ${PN}-keepalive-dev"

