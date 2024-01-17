SUMMARY = "Google Noto Fonts."
DESCRIPTION = "Google Noto Fonts."

HOMEPAGE = "https://www.google.com/get/noto/"
SECTION = "User Interface/X"

LICENSE = "OFL"
LIC_FILES_CHKSUM = "file://LICENSE_OFL.txt;md5=55719faa0112708e946b820b24b14097"

# Force extract location with subdir to match default ${S} location
SRC_URI = "file://NotoSans-hinted-light.zip;subdir=${BPN}-${PV}"
SRC_URI[md5sum] = "0e2007d8ee5ec0d65adc6657a40627f8"
SRC_URI[sha256sum] = "a1c403ecf62b6fd815a6bd0f94260e287fb291d3bad304be48717c8103a6cb2d"

# Workaround for multiprocess/rpmdeps-problem. Will not do FILEDEPS steps for
# noto-fonts, since it can lead to deadlock in do_package() step.
# https://patchwork.openembedded.org/patch/158773/
export SKIP_FILEDEPS_noto-fonts = "1"

do_install() {
    install -m 0755 -d ${D}/${datadir}/fonts/ttf/noto
    install -m 0644 -p ${S}/*.ttf ${D}/${datadir}/fonts/ttf/noto
}

FILES_${PN} += "${datadir}/fonts/ttf/noto/*.ttf"
