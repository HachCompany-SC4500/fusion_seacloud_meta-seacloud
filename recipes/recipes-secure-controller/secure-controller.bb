DESCRIPTION = "Install a script on the controller that disable the development \
mode and enable all security features configured for production environment. \
It is intended to be run before shipping a controller to the customer. \
Additionally, a systemd service ensures on each boot that the intended security \
level is enabled."

SECTION = "apps"
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""

SRC_URI = " \
    file://secure-system.sh \
    file://secure-system.service \
    file://uboot_shell_control.sh \
    file://secure_system_before_shipment.sh \
    file://90-secure-controller \
"

inherit systemd

SYSTEMD_SERVICE_${PN} = " \
    secure-system.service \
"

prefix = "/usr/local"
exec_prefix = "/usr/local"

do_install() {
    install -d ${D}/${bindir}/
    install -m 0500 ${WORKDIR}/secure-system.sh ${D}/${bindir}/
    install -m 0500 ${WORKDIR}/uboot_shell_control.sh ${D}/${bindir}/
    install -m 0555 ${WORKDIR}/secure_system_before_shipment.sh ${D}/${bindir}/

    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/secure-system.service ${D}/${sysconfdir}/systemd/system/

    install -d ${D}/${sysconfdir}/sudoers.d/
    install -m 0440 ${WORKDIR}/90-secure-controller ${D}/${sysconfdir}/sudoers.d/
}

FILES_${PN} = " \
    ${bindir}/secure-system.sh \
    ${bindir}/uboot_shell_control.sh \
    ${sysconfdir}/systemd/system/secure-system.service \
    ${bindir}/secure_system_before_shipment.sh \
    ${sysconfdir}/sudoers.d/90-secure-controller \
"
