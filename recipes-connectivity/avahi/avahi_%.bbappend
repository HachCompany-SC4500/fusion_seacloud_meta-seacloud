FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://avahi-daemon.conf \
    file://webserver.service \
"

# Hach Claros Network Bus (ClarosBus) requires standard ZeroConf support
# The libdns_sd provides a compatibility layer over avahi for this
PACKAGECONFIG = "dbus ${AVAHI_GTK} libdns_sd"
PACKAGECONFIG[libdns_sd] = "--enable-compat-libdns_sd,"

PACKAGES =+ "${@bb.utils.contains("PACKAGECONFIG", "libdns_sd", "libavahi-compat-libdnssd", "", d)}"

FILES_libavahi-compat-libdnssd = "${libdir}/libdns_sd.so.*"

#RPROVIDES_libavahi-compat-libdnssd = "libdns-sd"

do_install_append() {
    install -m 0644 ${WORKDIR}/avahi-daemon.conf ${D}/${sysconfdir}/avahi/avahi-daemon.conf

    # remove advertised by default services and add ours
    rm -f ${D}/${sysconfdir}/avahi/services/*
    install -m 0755 -d ${D}/${sysconfdir}/avahi/services/
    install -m 0644 ${WORKDIR}/*.service ${D}/${sysconfdir}/avahi/services/
}

FILES_avahi-daemon += " \
    ${sysconfdir}/avahi/avahi-daemon.conf \
    ${sysconfdir}/avahi/services/* \
"
