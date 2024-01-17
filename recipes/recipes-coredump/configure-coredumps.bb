#
# This recipe installs the files required by configure-coredumps.service
#

DESCRIPTION = "configure-coredumps service installation"
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""

SRC_URI = " \
    file://configure-coredumps.service \
    file://configure_coredumps.sh \
"

inherit systemd
SYSTEMD_SERVICE_${PN} = " \
    configure-coredumps.service \
"

bin_dir = "/usr/local/bin"

do_install() {
    install -d ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/configure_coredumps.sh ${D}/${bin_dir}

    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/configure-coredumps.service ${D}/${sysconfdir}/systemd/system
}

FILES_${PN} += " \
    ${bin_dir}/* \
    ${sysconfdir}/systemd/system/* \
"