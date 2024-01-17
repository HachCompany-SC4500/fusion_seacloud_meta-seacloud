FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

# Enable systemd iptc support to allow it to specify IP masquerading rules when
# IPMasquerade= directive is used.
# This is needed to implement network tethering.
PACKAGECONFIG_append = " \
    iptc \
"

# Clear the build configuration variable @dns-servers; no external DNS server
# will be implicitely set as a fallback.
# Systemd's default value for @dns-servers points to Google DNS servers,
# but we should not have such a configuration to be set automatically.
EXTRA_OEMESON += " \
    -Ddns-servers= \
"

# The patch 0003-Backport-fixes-about-timedatectl-for-systemd-v239.patch applies
# fixes that can be found in the systemd upstream repository, namely the
# following commits:
#     * 2770af85ac04fd14af2f6bcdf4d3967ed6f2e36f
#     * 3af0a96c0fcc623bd16649fc3640396a657cf9ef
#     * 84a87726eec88e7b11c8aa633bca006a0c0fc435
#     * b4356b5720ae0974f1f8962e26562591dd0be9e9
# The four commits listed above are included in systemd v241.
SRC_URI += " \
    file://bridge.netdev \
    file://bridged.network \
    file://br0.network \
    file://fec0.network \
    file://fec1.network \
    file://usb-ethernet.network \
    file://tmp.conf \
    file://timesyncd.conf \
    file://10-KillUserProcesses.conf \
    file://0001-Disable-the-DNS-stub-resolver-of-systemd-resolved.patch \
    file://0002-Drop-fallback-address-when-a-DHCP-lease-is-acquired.patch \
    file://0003-Backport-fixes-about-timedatectl-for-systemd-v239.patch \
    file://0004-Disable-systemd-networkd-wait-online.service.patch \
"

do_install_append() {
    # Install the network configuration file. Interfaces not managed by connman
    install -d ${D}${sysconfdir}/${PN}/
    install -m 0644 ${WORKDIR}/timesyncd.conf ${D}${sysconfdir}/${PN}/

    install -d ${D}${sysconfdir}/${PN}/network
    install -m 0644 ${WORKDIR}/bridge.netdev ${D}${sysconfdir}/${PN}/network/
    install -m 0644 ${WORKDIR}/bridged.network ${D}${sysconfdir}/${PN}/network/
    install -m 0644 ${WORKDIR}/usb-ethernet.network ${D}${sysconfdir}/${PN}/network/
    install -m 0644 ${WORKDIR}/br0.network ${D}${sysconfdir}/${PN}/network/
    install -m 0644 ${WORKDIR}/fec0.network ${D}${sysconfdir}/${PN}/network/
    install -m 0644 ${WORKDIR}/fec1.network ${D}${sysconfdir}/${PN}/network/

    install -d ${D}${sysconfdir}/${PN}/logind.conf.d/
    install -m 0644 ${WORKDIR}/10-KillUserProcesses.conf ${D}${sysconfdir}/${PN}/logind.conf.d/

    install -d ${D}${exec_prefix}/lib/tmpfiles.d/
    install -m 0644 ${WORKDIR}/tmp.conf ${D}${exec_prefix}/lib/tmpfiles.d/
}
