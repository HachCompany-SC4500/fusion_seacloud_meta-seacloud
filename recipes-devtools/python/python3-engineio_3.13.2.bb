SUMMARY = "Engine.IO server"
HOMEPAGE = "http://github.com/miguelgrinberg/python-engineio/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=42d0a9e728978f0eeb759c3be91536b8"

SRC_URI = "git://github.com/miguelgrinberg/python-engineio;protocol=https;branch=main"
SRCREV = "adaf2f143df206a7c357ef68f2fa2cc5ce3f392c"

S = "${WORKDIR}/git"

inherit setuptools3

PACKAGECONFIG ?= "client"
PACKAGECONFIG[client] = ",,, \
	${PYTHON_PN}-requests \
	${PYTHON_PN}-websocket-client \
"

RDEPENDS_${PN} += " \
	${PYTHON_PN}-core \
	${PYTHON_PN}-six \
"
