
SUMMARY = "smbus2 is a drop-in replacement for smbus-cffi/smbus-python in pure Python"
HOMEPAGE = "https://github.com/kplindegaard/smbus2"
AUTHOR = "Karl-Petter Lindegaard <kp.lindegaard@gmail.com>"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://setup.py;md5=94acccf59a9fff67405fc46161f8dccf"

SRC_URI = "https://files.pythonhosted.org/packages/6a/06/80a6928e5cbfd40c77c08e06ae9975c2a50109586ce66435bd8166ce6bb3/smbus2-0.3.0.tar.gz"
SRC_URI[md5sum] = "d5ed5acc889b4770a84cc932853ed20a"
SRC_URI[sha256sum] = "210e66eebe4d0b1fe836b3ec2751841942e1c4918c0b429b20a0e20a222228b4"

S = "${WORKDIR}/smbus2-0.3.0"

RDEPENDS_${PN} = ""

inherit setuptools
