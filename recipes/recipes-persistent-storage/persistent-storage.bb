DESCRIPTION = "Persistent storage"

LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""

require persistent-storage.inc

DEPENDS_${PN}= "persistent-crypto"

SRC_URI = "\
	file://persistent-storage-update \
	file://persistent-storage-init \
	${FCC_SRC_URI} \
"

inherit useradd
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM_${PN} = "--system -g 995 _befe; --system -g 992 _fcc_extra_group"

S = "${WORKDIR}/git"

# This compilation step is used to call the Makefile located in "fusion_fw/merge" of the Fusion_FW_common repository,
# so that the files generated by this Makefile are included in the persistent.tar.xz archive.
# The goal of the Makefile is to create the symbolic links for language specific device driver files (PD, RB/TR) for
# those sensors running with a version whose corresponding DD language files are not in the controller
# See Fusion_FW_common/fusion_fw/merge/Make for details
do_compile(){
	cd fusion_fw
	TOP=`pwd`
	export TOP
	make -C merge ARCH=IMX7D ROOTFSTOP=${STAGING_DIR_HOST} TARGET="EAGLE" VERBOSE=Y all
}

do_install() {
	mkdir -p ${WORKDIR}/persistent
	mkdir -p ${WORKDIR}/persistent_init

	# Copy Eagle specific files for persistent partition
	cp -r ${WORKDIR}/persistent-storage-update/. ${WORKDIR}/persistent

	# Copy merged files of fusion common code (fcc)
	cp -r ${WORKDIR}/git/fusion_fw/merge/mnt/fcc/* ${WORKDIR}/persistent/fcc

	chgrp -R _befe ${WORKDIR}/persistent/befe
	chmod -R 0660 ${WORKDIR}/persistent/befe
	chgrp -R _fcc_extra_group ${WORKDIR}/persistent/fcc
	chmod -R 0660 ${WORKDIR}/persistent/fcc
	chgrp -R root ${WORKDIR}/persistent/fcc/etc
	chmod -R 0600 ${WORKDIR}/persistent/fcc/etc

	# Create a directory on the persistent partition to hold the configuration files of connections handled by connman.
	# If for any reason, the directory does not exist, it is added back on package installation. This does not remove its content.
	install -d -o root -g root -m 0700 ${WORKDIR}/persistent/system/connman

	# Make the directories in the persistent partition explorable ('x' bit) and
	# enable their setgid bit so that files and directories created under them
	# inherit their group ownership.
	find ${WORKDIR}/persistent/ -type d -exec chmod 2770 {} \;

	# copy and setup permissions for needed files which are a part of persistent_init
	cp -r ${WORKDIR}/persistent-storage-init/. ${WORKDIR}/persistent_init
	ln -sf nebula.properties_hachtest ${WORKDIR}/persistent_init/fcc/set/nebula.properties

	chgrp -R _fcc_extra_group ${WORKDIR}/persistent_init/fcc
	chmod -R 0660 ${WORKDIR}/persistent_init/fcc

	# Make directories explorable and enable their setgid bit
	find ${WORKDIR}/persistent_init/ -type d -exec chmod 2770 {} \;

	tar cfJ ${WORKDIR}/persistent.tar.xz -C ${WORKDIR}/persistent .
	tar cfJ ${WORKDIR}/persistent_init.tar.xz -C ${WORKDIR}/persistent_init .

	# Create a special archive of the persistent partition for the Tezi image that contain an additional file
	# named "development". This file indicates that the controller is in development mode, and prevents system
	# services to close the open system accesses (empty root password accessible via the serial console or via SSH)
	# needed for the development phase.
	#
	# This file will be removed by running the script "secure_system_before_shipment.sh" on the controller
	# before deploying it (normally automatically done by FIT). The special archive for Tezi is necessary because
	# we absolutely don't want the "development" file to pop back following an SWUpdate image installation.
	touch ${WORKDIR}/development
	tar cfJ ${WORKDIR}/persistent-tezi.tar.xz -C ${WORKDIR}/persistent . -C ${WORKDIR}/persistent_init . -C ${WORKDIR} ./development

	rm -rf ${WORKDIR}/persistent
	rm -rf ${WORKDIR}/persistent_init

	# /media/persistent would also be created by /etc/persistent-crypto.sh
	# The purpose of creating it explicitely is to ensure that _befe
	# group will be added to image. It is not included if no files are deployed in a package.
	mkdir -p ${D}/media/persistent
}

inherit deploy
addtask deploy before do_build after do_install

do_deploy() {
	cp ${WORKDIR}/persistent.tar.xz ${DEPLOYDIR}
	cp ${WORKDIR}/persistent_init.tar.xz ${DEPLOYDIR}
	cp ${WORKDIR}/persistent-tezi.tar.xz ${DEPLOYDIR}
}

FILES_${PN} += "/media/persistent"

PACKAGE_ARCH = "${MACHINE_ARCH}"
