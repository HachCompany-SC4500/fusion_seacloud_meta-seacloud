FILESEXTRAPATHS_prepend := "${THISDIR}/udev:"

SRC_URI += " \
    file://bridge-mac-configure.sh \
    file://bridge.rules \
    file://20-ethernet.rules \
    file://94-modems.rules \
    file://95-touchscreen-filter.rules \
"

do_install_append() {
    install -d ${D}${sysconfdir}/udev/scripts/
    install -m 0755 ${WORKDIR}/bridge-mac-configure.sh ${D}${sysconfdir}/udev/scripts/

    install -d ${D}${sysconfdir}/udev/rules.d/
    install -m 0644 ${WORKDIR}/bridge.rules ${D}${sysconfdir}/udev/rules.d/
    # Install the rules file to rename eth0 and eth1 interfaces
    install -m 0644 ${WORKDIR}/20-ethernet.rules ${D}${sysconfdir}/udev/rules.d/
    install -m 0644 ${WORKDIR}/94-modems.rules ${D}${sysconfdir}/udev/rules.d/
    install -m 0644 ${WORKDIR}/95-touchscreen-filter.rules ${D}${sysconfdir}/udev/rules.d/
}
