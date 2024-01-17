DESCRIPTION = "Cukinia - a Linux firmware validation framework"
SECTION = "tools"
DEPENDS=""
LICENSE = "Apache-2.0 & GPLv3"
LIC_FILES_CHKSUM = "file://${S}/LICENSE;md5=e3fc50a88d0a364313df4b21ef20c29e \
		    file://${S}/LICENSE.GPLv3;md5=d32239bcb673463ab874e80d47fae504 \
		    "


SRC_URI = "git://github.com/savoirfairelinux/cukinia.git;protocol=https;branch=${SRCBRANCH}"

SRCBRANCH="master"
# Tag v0.6.0
SRCREV="3fd9db9838ef3de20965aa5f7657c363b679a995"

S = "${WORKDIR}/git"

do_install() {
    install -d ${D}/${bindir}
    install -m 755 ${S}/cukinia ${D}/${bindir}
}

FILES_${PN} += "\
    ${bindir}/cukinia \
"
