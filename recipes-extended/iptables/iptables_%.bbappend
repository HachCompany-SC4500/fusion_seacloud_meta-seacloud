FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://iptables.service \
    file://ip6tables.service \
    file://iptables.sh \
    file://ip6tables.sh \
    file://iptables_dev.sh \
"

inherit systemd

SYSTEMD_SERVICE_${PN} = " \
    iptables.service \
    ip6tables.service \
"

exec_dir = "/usr/local/bin"

do_install_append() {
    install -d ${D}/${exec_dir}/
    install -m 0700 ${WORKDIR}/iptables.sh ${D}/${exec_dir}/
    install -m 0700 ${WORKDIR}/ip6tables.sh ${D}/${exec_dir}/
    install -m 0700 ${WORKDIR}/iptables_dev.sh ${D}/${exec_dir}/

    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/iptables.service ${D}/${sysconfdir}/systemd/system/
    install -m 0644 ${WORKDIR}/ip6tables.service ${D}/${sysconfdir}/systemd/system/
}

FILES_${PN} += " \
    ${exec_dir}/iptables.sh \
    ${exec_dir}/ip6tables.sh \
    ${exec_dir}/iptables_dev.sh \
    ${sysconfdir}/systemd/system/iptables.service \
    ${sysconfdir}/systemd/system/ip6tables.service \
"
