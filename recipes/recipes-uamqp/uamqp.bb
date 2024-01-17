DESCRIPTION = "uAMQP library" 
SECTION = "libs" 
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=4283671594edec4c13aeb073c219237a"
PR = "r0" 

DEPENDS = " openssl util-linux"

# uamqp only creates static libs, so only uamqp-staticdev package will be generated and no uamqp-dev package (shared library package).
# By default, uamqp-staticdev depends on uamqp-dev. To avoid that Yocto complains about uamqp-dev package missing during SDK build,
# we remove the dependency of uamqp-staticdev package on uamqp-dev package
RDEPENDS_${PN}-dev = ""

#SRCREV = "87c15855ef9b64b20ce3d94a9cd02717ea8c04d6"

# Release 14/12/2017
#SRCREV = "079e530ed7892e09934aad3654031aa2f2d07539"

# Release "release_2018_01_12_after_bump_version"
SRCREV = "ec0e29371e14e6e1c9a1629597f3b4edb2a37dba"



SRCBRANCH = "master"
SRC_URI = "gitsm://github.com/Azure/azure-uamqp-c.git;protocol=https;branch=${SRCBRANCH}"

SRC_URI += "file://0001-Dusseldorf-additional-patch.patch"
S = "${WORKDIR}/git"

#SRC_URI = "file://azure-uamqp-c-87c15855ef9b64b20ce3d94a9cd02717ea8c04d6.tar.gz "
#S = "${WORKDIR}/azure-uamqp-c-87c15855ef9b64b20ce3d94a9cd02717ea8c04d6/"

inherit cmake pkgconfig pythonnative

EXTRA_OECMAKE = "\
    -Dmemory_trace:BOOL=ON \
    -Duse_condition:STRING=ON \
    -Duse_wsio:BOOL=OFF \
    -Dskip_unittests:BOOL=ON \
    -Duse_openssl:BOOL=ON  \
    -DBUILD_TESTING:BOOL=OFF \
    -Duse_schannel:bool=OFF \
    -Duse_wolfssl:bool=OFF \
    -Duse_http:bool=OFF \
    -Dskip_samples:BOOL=ON \
    -DCMAKE_BUILD_TYPE:STRING=Debug \
"

TARGET_CFLAGS += "-fPIC"

#RM_WORK_EXCLUDE += " uamqp"

do_install (){
        cmake_do_install
        install ${S}/../build/libuamqp.a ${D}/${libdir}
# The following lines have been added to put the header files in the same folders as FPM did
        rm -rf ${D}/${includedir}/azure_uamqp_c
        mkdir -p ${D}/${includedir}/azure_uamqp_c
        install ${S}/inc/azure_uamqp_c/* ${D}/${includedir}/azure_uamqp_c
        rm -rf ${D}/${includedir}/azure_c_shared_utility
        mkdir -p ${D}/${includedir}/azure_c_shared_utility
        install ${S}/deps/azure-c-shared-utility/inc/azure_c_shared_utility/*.h    ${D}/${includedir}/azure_c_shared_utility
}
