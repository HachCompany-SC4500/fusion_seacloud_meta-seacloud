DESCRIPTION = "Option key decoder executable"
LICENSE = "CLOSED"


DEPENDS += " openssl"
INSANE_SKIP_${PN} = "ldflags"

FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
	file://option-key-decoder.c \
"

local_bindir = "/usr/local/bin"

do_compile() {
	${CC} ${WORKDIR}/option-key-decoder.c -lssl -lcrypto -O3 -o ${WORKDIR}/option-key-decoder
}

do_install () {
	install -d ${D}${local_bindir}
	install -m 550 ${WORKDIR}/option-key-decoder ${D}${local_bindir}/
}

FILES_${PN} += " \
	${local_bindir}/option-key-decoder \
"
