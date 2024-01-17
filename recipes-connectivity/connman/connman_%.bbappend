FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += " \
	file://main.conf.reference \
	file://0001-Customized-version.patch \
	file://0001-Enable-roaming-Telenor.patch \
	file://0002-Ensure-that-connman-is-started-after-the-persistent.patch \
	file://0005-Don-t-prevent-systemd-resolved.service-with-connman.patch \
	file://0006-dns-support-for-systemd-resolved.patch \
	file://0007-Disconnecting-an-interface-only-remove-its-own-routes.patch \
"

EXTRA_OECONF += " --with-dns-backend=systemd-resolved"

do_install_append() {
	# install sea cloud configuration file for connman 
	install -d ${D}${sysconfdir}/${BPN}/
	install -m 0644 ${WORKDIR}/main.conf.reference ${D}${sysconfdir}/${BPN}/
	ln -sf /etc/connman/main.conf.reference ${D}${sysconfdir}/${BPN}/main.conf

	sed -i '/resolv.conf/d' ${D}${sysconfdir}/tmpfiles.d/connman_resolvconf.conf

	install -d ${D}/var/lib
	ln -s /media/persistent/system/connman ${D}/var/lib/connman
}

FILES_${PN} += " \
	/var/lib/connman \
"

ALTERNATIVE_${PN} = ""
ALTERNATIVE_TARGET[resolv-conf] = ""
ALTERNATIVE_LINK_NAME[resolv-conf] = ""
