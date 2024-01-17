DESCRIPTION = "garbage collector"
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""

inherit systemd
SYSTEMD_SERVICE_${PN} += " \
	garbage_collector.timer \
"

SRC_URI += " \
	file://garbage_collector.sh \
	file://garbage_collector@.service \
	file://garbage_collector.timer \
	file://garbage_collector_core.path \
	file://garbage_collector_logs.path \
"

bin_dir = "/usr/local/bin"

do_install () {
	install -d ${D}/${bin_dir}
	install -m 0500 ${WORKDIR}/garbage_collector.sh ${D}/${bin_dir}

	install -d ${D}/${sysconfdir}/systemd/system
	install -m 0644 ${WORKDIR}/garbage_collector@.service ${D}/${sysconfdir}/systemd/system
	install -m 0644 ${WORKDIR}/garbage_collector.timer ${D}/${sysconfdir}/systemd/system
	install -m 0644 ${WORKDIR}/garbage_collector_core.path ${D}/${sysconfdir}/systemd/system
	install -m 0644 ${WORKDIR}/garbage_collector_logs.path ${D}/${sysconfdir}/systemd/system
}

FILES_${PN} += " \
	${bin_dir}/* \
	${sysconfdir}/systemd/system/* \
"
