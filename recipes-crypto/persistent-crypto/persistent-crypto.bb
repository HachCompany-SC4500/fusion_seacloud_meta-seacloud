DESCRIPTION = "Persistent crypto service"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit systemd

DEPENDS_${PN} = "kb-tool cryptsetup cryptodev-module cryptodev-tests "

FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
	file://${PN}.service \
	file://${PN}.sh \
	file://persistent-core.sh \
	file://persistent-mount-both.sh \
"

SYSTEMD_SERVICE_${PN} = "${PN}.service"

local_bindir = "/usr/local/bin"

do_install () {
	install -d 440 ${D}${sysconfdir}/
	install -d 440 ${D}${systemd_unitdir}/system/
	install -m 550 ${WORKDIR}/${PN}.sh ${D}${sysconfdir}/
	install -m 644 ${WORKDIR}/${PN}.service ${D}${systemd_unitdir}/system/
	install -m 550 ${WORKDIR}/persistent-core.sh ${D}${sysconfdir}/

	install -d ${D}${local_bindir}
	install -m 550 ${WORKDIR}/persistent-mount-both.sh ${D}${local_bindir}/
}

FILES_${PN} += " \
	${sysconfdir} \
	${local_bindir}/persistent-mount-both.sh \
"
