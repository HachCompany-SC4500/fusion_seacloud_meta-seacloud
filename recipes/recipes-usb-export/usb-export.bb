DESCRIPTION = "Install a script on the controller which purpose is to export system logs to a USB stick"

SECTION = "apps"
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""

RDEPENDS_${PN} = "bash python3-core"

SRC_URI = " \
    file://device_logs.py \
    file://create_diag_report.sh \
    file://create_service_logs.sh \
    file://get_connectivity_details.sh \
"

prefix = "/usr/local"
exec_prefix = "/usr/local"

do_install() {
    install -d ${D}/${bindir}/
    install -m 0555 ${WORKDIR}/device_logs.py ${D}/${bindir}/
    install -m 0555 ${WORKDIR}/create_diag_report.sh ${D}/${bindir}/
    install -m 0555 ${WORKDIR}/create_service_logs.sh ${D}/${bindir}/
    install -m 0555 ${WORKDIR}/get_connectivity_details.sh ${D}/${bindir}/
}

FILES_${PN} = " \
    ${bindir}/device_logs.py \
    ${bindir}/create_diag_report.sh \
    ${bindir}/create_service_logs.sh \
    ${bindir}/get_connectivity_details.sh \
"
