DESCRIPTION = "RL78 firmware file(s) installation" 
SUMMARY = "This recipe installs RL78 firmware file(s) in /backup folder of the image" 
LICENSE = "CLOSED"
PV = "1.0.0"

include recipes/recipes-rl78-firmware/rl78-firmware.inc

do_install() {
    install -d ${D}/backup

    # The recipe expects the build system to inject the filesSRC_URI, which is especified in rl78-firmware.inc
    install -m 0755 ${WORKDIR}/source/* ${D}/backup
}

FILES_${PN} += "\
    /backup/* \
"
