FILESEXTRAPATHS_prepend := "${THISDIR}/systemd:"

SRC_URI += " \
    file://journald.conf \
"

do_install_append() {
    install -d ${D}${sysconfdir}/systemd/
    install -m 0644 ${WORKDIR}/journald.conf ${D}${sysconfdir}/systemd/

    # Configure persistent journald logs
    sed -i 's/#Storage=auto/Storage=persistent/g' ${D}/etc/systemd/journald.conf
}

FILES_${PN} += " \
    ${sysconfdir}/systemd/journald.conf \
"
