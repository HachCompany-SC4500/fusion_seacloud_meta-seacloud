
do_install_append() {
	# Enable net.ipv4.ip_forward
	sed -i "s/#net.ipv4.ip_forward/net.ipv4.ip_forward/" ${D}${sysconfdir}/sysctl.conf
}
