FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += "\
    file://90-tslib.conf \
"

do_install_append() {
    install -d ${D}/${datadir}/X11/xorg.conf.d
    install -m 0644 ${WORKDIR}/90-tslib.conf ${D}/${datadir}/X11/xorg.conf.d
}

FILES_${PN} += " \
    ${datadir}/X11/xorg.conf.d/90-tslib.conf \
"

 