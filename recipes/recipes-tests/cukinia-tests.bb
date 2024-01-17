DESCRIPTION = "Cukinia - test set"
SECTION = "tools"
LICENSE = "CLOSED"
RDEPENDS_${PN}="cukinia bash"

SRC_URI = "file://eagle.conf \
	   file://test_fs.sh \
	   file://ext2.img.tar.gz;unpack=0 \
	   file://ext3.img.tar.gz;unpack=0 \
	   file://ext4.img.tar.gz;unpack=0 \
	   file://fat12.img.tar.gz;unpack=0 \
	   file://fat16.img.tar.gz;unpack=0 \
	   file://fat32.img.tar.gz;unpack=0 \
	   file://exfat.img.tar.gz;unpack=0 \
	   file://ntfs.img.tar.gz;unpack=0 \
"

do_install() {
    install -d ${D}/${datadir}/cukinia/
    install -d ${D}/${sysconfdir}/cukinia/
    install -m 755 ${WORKDIR}/eagle.conf ${D}/${datadir}/cukinia/
    ln -sfn ${datadir}/cukinia/eagle.conf ${D}/${sysconfdir}/cukinia/cukinia.conf
    install -m 755 ${WORKDIR}/test_fs.sh ${D}/${datadir}/cukinia/
    
    install -d ${D}/${datadir}/cukinia/fs_images
    install -m 755 ${WORKDIR}/ext2.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/ext3.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/ext4.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/fat12.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/fat16.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/fat32.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/exfat.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
    install -m 755 ${WORKDIR}/ntfs.img.tar.gz ${D}/${datadir}/cukinia/fs_images/
}

FILES_${PN} += "\
    ${datadir}/cukinia/eagle.conf \
    ${datadir}/cukinia/test_fs.sh \
    ${datadir}/cukinia/fs_images/* \
"
