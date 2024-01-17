SUMMARY = "Socket.IO server"
HOMEPAGE = "http://github.com/miguelgrinberg/python-socketio/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=42d0a9e728978f0eeb759c3be91536b8"

SRC_URI = "git://github.com/miguelgrinberg/python-socketio;protocol=https;branch=main"
SRCREV = "d49d6987f4c8e780dab30d6e6bcdaa4910f3e7c1"

S = "${WORKDIR}/git"

inherit setuptools3

PACKAGECONFIG ?= "client"
PACKAGECONFIG[client] = ",,, \
	${PYTHON_PN}-requests \
	${PYTHON_PN}-websocket-client \
"

RDEPENDS_${PN} += " \
	${PYTHON_PN}-core \
	${PYTHON_PN}-engineio \
	${PYTHON_PN}-six \
"
