FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://hosts \
"

do_install_append() {
    install -d ${D}/${sysconfdir}/
    install -m 0644 ${WORKDIR}/hosts ${D}/${sysconfdir}/
}

FILES_${PN} += " \
    ${sysconfdir}/hosts \
"
