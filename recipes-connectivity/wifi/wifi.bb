#
# This recipe installs python3 scripts and Systemd unit files related to wifi management
#

DESCRIPTION = "Python scripts to manage Wifi connectivity"
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""
PYTHON_VERSION = "3.5"

SRC_URI = " \
    file://lib_wifi.py \
    file://config_wifi.py \
    file://wifi_rssi_monitor.sh \
    file://wifi_rssi_monitor_worker.py \
    file://wifi_logger.py \
    file://wifi_rssi_monitor.service \
    file://wifi_rssi_monitor.timer \
    file://wifi_logger.service \
    file://wifi_logger.timer \
"

RDEPENDS_${PN} = " \
    python3-core \
    custom-python3-libs \
"

inherit systemd
SYSTEMD_AUTO_ENABLE_${PN} = "enable"
SYSTEMD_SERVICE_${PN} = " \
    wifi_logger.timer \
    wifi_rssi_monitor.timer \
"

bin_dir = "/usr/local/bin"
python_libdir = "/usr/lib/python${PYTHON_VERSION}"

do_install() {
    install -d ${D}/${python_libdir}
    install -m 0644 ${WORKDIR}/lib_wifi.py ${D}/${python_libdir}

    install -d ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/config_wifi.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/wifi_logger.py ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/wifi_rssi_monitor.sh ${D}/${bin_dir}
    install -m 0755 ${WORKDIR}/wifi_rssi_monitor_worker.py ${D}/${bin_dir}

    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/wifi_logger.timer ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/wifi_logger.service ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/wifi_rssi_monitor.timer ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/wifi_rssi_monitor.service ${D}/${sysconfdir}/systemd/system
}

FILES_${PN} += " \
    ${bin_dir}/* \
    ${python_libdir}/* \
    ${sysconfdir}/systemd/system/* \
"
