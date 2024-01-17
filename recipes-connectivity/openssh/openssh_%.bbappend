FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://CA.pub \
    file://sshd_config \
    file://revoked_keys \
    file://authorized_keys \
    file://tcp-timestamp.conf \
"

inherit useradd

USERADD_PACKAGES = "${PN}-sshd"
GROUPADD_PARAM_${PN}-sshd = "--system ssh-allowed; --system ssh-allowed-tmp"

do_install_append() {
    install -m 0600 ${WORKDIR}/CA.pub ${D}/${sysconfdir}/ssh/CA.pub
    install -m 0644 ${WORKDIR}/sshd_config ${D}/${sysconfdir}/ssh/sshd_config
    install -m 0644 ${WORKDIR}/sshd_config ${D}/${sysconfdir}/ssh/sshd_config_readonly
    install -m 0644 ${WORKDIR}/sshd_config ${D}/${sysconfdir}/ssh/sshd_config_prod
    install -m 0600 ${WORKDIR}/revoked_keys ${D}/${sysconfdir}/ssh/revoked_keys

    install -d 0700 ${D}/home/root/.ssh
    install -m 0600 ${WORKDIR}/authorized_keys ${D}/home/root/.ssh/authorized_keys

    install -d ${D}/${sysconfdir}/sysctl.d/
    install -m 0644 ${WORKDIR}/tcp-timestamp.conf ${D}/${sysconfdir}/sysctl.d/
}

FILES_${PN}-sshd += " \
    ${sysconfdir}/ssh/sshd_config \
    ${sysconfdir}/ssh/sshd_config_readonly \
    ${sysconfdir}/ssh/sshd_config_prod \
    ${sysconfdir}/ssh/revoked_keys \
    /home/root/.ssh/authorized_keys \
    ${sysconfdir}/sysctl.d/tcp-timestamp.conf \
"
