FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += "\
        file://ts.conf \
	file://ts_uinput.service \
"

inherit systemd

SYSTEMD_SERVICE_${PN} = "ts_uinput.service"
SYSTEMD_AUTO_ENABLE = "disable"

do_install_append() {
    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/ts_uinput.service ${D}/${sysconfdir}/systemd/system/
}

FILES_${PN} += " \
    ${sysconfdir}/systemd/system/ts_uinput.service \
"

