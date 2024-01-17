#
# This recipe installs calibration stuff related to user input device
#

DESCRIPTION = "Calibration stuff related to user input device"
LICENSE = "CLOSED"

SRC_URI = "\
        file://uinput_calibration.sh \
        file://uinput_calibration.service \
"

inherit systemd

SYSTEMD_SERVICE_${PN} = "uinput_calibration.service"
SYSTEMD_AUTO_ENABLE = "enable"

bin_dir = "/usr/local/bin"

do_install() {
    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/uinput_calibration.service ${D}/${sysconfdir}/systemd/system/

    install -d ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/uinput_calibration.sh ${D}/${bin_dir}
}

FILES_${PN} += " \
    ${bin_dir}/* \
    ${sysconfdir}/systemd/system/* \
"
