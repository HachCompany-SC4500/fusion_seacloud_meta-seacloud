DESCRIPTION = "Qpid proton library" 
SECTION = "libs" 
# LICENSE = "GPL" 
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""
PR = "r0" 

DEPENDS = " openssl util-linux"
# ossp-uuid 

SRC_URI = "file://qpid-proton-0.7.tar.gz \
		   file://0001-Patch-from-emdist.patch"

S = "${WORKDIR}/qpid-proton-0.7/"

inherit cmake pkgconfig pythonnative

EXTRA_OECMAKE = "-DSYSINSTALL_BINDINGS=OFF -DBUILD_CPP=OFF -DNOBUILD_JAVA=1 -DBUILD_PERL=OFF -DBUILD_PHP=OFF -DNOBUILD_PYTHON=1 -DNOBUILD_RUBY=1 -DUUID_GENERATE_IN_UUID:INTERNAL=Y"

# Move useless files in dbg package
FILES_${PN}-dbg += "${datadir}/proton/ \
 		    ${datadir}/proton-0.7/ \ 
                    ${libdir}/cmake/Proton/"
