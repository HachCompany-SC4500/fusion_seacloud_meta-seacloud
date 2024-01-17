FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://sudoers \
"

do_install_append() {
    install -d ${D}/${sysconfdir}
    install -m 0440 ${WORKDIR}/sudoers ${D}/${sysconfdir}
}

FILES_${PN} += " \
    ${sysconfdir}/sudoers \
"
