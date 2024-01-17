FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

inherit useradd

SRC_URI += " \
    file://runOpenvpn.sh \
    file://openvpn.service \
    file://openvpn.path \
"

SYSTEMD_SERVICE_${PN} += "openvpn.service"
SYSTEMD_AUTO_ENABLE = "disable"

USERADD_PACKAGES = "${PN}"

username = "_openvpn"
userdesc = "User running OpenVPN daemon"
homedirloc = "/var/lib/openvpn"
usershell = "/sbin/nologin"
USERADD_PARAM_${PN} = "--system --user-group --home-dir ${homedirloc} \
    --shell ${usershell} --comment \"${userdesc}\" ${username}"

local_bindir = "/usr/local/bin"

do_configure_append() {
    sed -i -e "s/%OPENVPN_USER%/${username}/" ${WORKDIR}/runOpenvpn.sh
    sed -i -e "s/%OPENVPN_GROUP%/${username}/" ${WORKDIR}/runOpenvpn.sh
}

do_install_append(){
    install -d ${D}/${local_bindir}
    install -m 0555 ${WORKDIR}/runOpenvpn.sh ${D}/${local_bindir}

    install -d ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/openvpn.service ${D}/${sysconfdir}/systemd/system
    install -m 0644 ${WORKDIR}/openvpn.path ${D}/${sysconfdir}/systemd/system
}

pkg_preinst_append_${PN}() {

# create a home directory for the dedicated user
install -d -m 0700 -o ${username} -g ${username} "$D${homedirloc}"
}

FILES_${PN} += " \
    ${local_bindir}/runOpenvpn.sh \
    ${sysconfdir}/systemd/system \
"
