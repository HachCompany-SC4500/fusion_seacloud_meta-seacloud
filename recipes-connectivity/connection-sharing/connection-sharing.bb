DESCRIPTION = "Connection sharing support package"
LICENSE = "CLOSED"

inherit systemd

RDEPENDS_${PN} = " \
	dnsmasq \
	python3-core \
	custom-python3-libs \
"

FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
	file://config_sharenet.py \
	file://sharenet_configuration_loader.service \
	file://config_ethernet_ports_mode.py \
	file://ethernet_ports_mode_configuration_sender.service \
	file://ethernet_ports_mode_configuration_sender.timer \
"

SYSTEMD_SERVICE_${PN} = " \
	sharenet_configuration_loader.service \
	ethernet_ports_mode_configuration_sender.timer \
"

do_install () {
	install -d 440 ${D}${sysconfdir}/systemd/system
	install -m 644 ${WORKDIR}/sharenet_configuration_loader.service ${D}/${sysconfdir}/systemd/system
	install -m 644 ${WORKDIR}/ethernet_ports_mode_configuration_sender.service ${D}/${sysconfdir}/systemd/system
	install -m 644 ${WORKDIR}/ethernet_ports_mode_configuration_sender.timer ${D}/${sysconfdir}/systemd/system

	install -d ${D}/usr/local/bin
	install -m 550 ${WORKDIR}/config_sharenet.py ${D}/usr/local/bin
	install -m 550 ${WORKDIR}/config_ethernet_ports_mode.py ${D}/usr/local/bin
}

FILES_${PN} += " \
	/usr/local/bin/config_sharenet.py \
	${sysconfdir}/systemd/system/sharenet_configuration_loader.service \
	/usr/local/bin/config_ethernet_ports_mode.py \
	${sysconfdir}/systemd/system/ethernet_ports_mode_configuration_sender.service \
	${sysconfdir}/systemd/system/ethernet_ports_mode_configuration_sender.timer \
"
