
SUMMARY = "A library to drive a Bosch BME280 temperature, humidity, pressure sensor over I2C"
HOMEPAGE = "https://github.com/rm-hull/bme280"
AUTHOR = "Richard Hull <richard.hull@destructuring-bind.org>"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE.rst;md5=bb3575ca767ecc801d139a2ceebee86f"

SRC_URI = "https://files.pythonhosted.org/packages/0a/25/486a1ec01bfd3490987ed7f0f75e475e09242c0057d6a2e0d22d56b77046/RPi.bme280-0.2.3.tar.gz"
SRC_URI[md5sum] = "5924824c8862927b6850b9a2ef91bc28"
SRC_URI[sha256sum] = "11c25e549b7f3ef2e41d463195e04994ef7add9e8ccd2616ccf58d322d783b9c"

S = "${WORKDIR}/RPi.bme280-0.2.3"

RDEPENDS_${PN} = ""

inherit setuptools
