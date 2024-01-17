#
# This recipe installs python3 scripts and Systemd unit files related to cellular management
#

DESCRIPTION = "Python scripts to manage cellular connectivity"
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""
PYTHON_VERSION = "3.5"

SRC_URI = " \
    file://lib_modem.py \
    file://lib_cellular_stats.py \
    file://config_modem.py \
    file://cellular_signal_strength_monitor.py \
    file://cellular_data_supervisor.py \
    file://reboot_modem.sh \
    file://switch_firmware_usmodem.py \
    file://log_modem_detection.py \
    file://multitech_factory_reset.sh \
    file://modem_configuration_loader.service \
    file://cellular_data_supervisor.timer \
    file://cellular_data_supervisor.service \
    file://cellular_signal_strength_monitor.service \
"

RDEPENDS_${PN} = " \
    python3-core \
    custom-python3-libs \
    bash \
"

inherit systemd
SYSTEMD_AUTO_ENABLE_${PN} = "enable"
SYSTEMD_SERVICE_${PN} = " \
    modem_configuration_loader.service \
"

bin_dir = "/usr/local/bin"
python_libdir = "/usr/lib/python${PYTHON_VERSION}"

do_install() {
    install -d ${D}/${python_libdir}
    install -m 0644 ${WORKDIR}/lib_modem.py ${D}/${python_libdir}
    install -m 0644 ${WORKDIR}/lib_cellular_stats.py ${D}/${python_libdir}

    install -d ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/config_modem.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/cellular_signal_strength_monitor.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/cellular_data_supervisor.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/reboot_modem.sh ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/switch_firmware_usmodem.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/log_modem_detection.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/multitech_factory_reset.sh ${D}/${bin_dir}

    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/modem_configuration_loader.service ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/cellular_data_supervisor.timer ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/cellular_data_supervisor.service ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/cellular_signal_strength_monitor.service ${D}/${sysconfdir}/systemd/system
}

FILES_${PN} += " \
    ${bin_dir}/* \
    ${python_libdir}/* \
    ${sysconfdir}/systemd/system/* \
"
