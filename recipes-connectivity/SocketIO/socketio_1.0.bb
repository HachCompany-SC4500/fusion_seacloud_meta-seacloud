DESCRIPTION = "Eagle SocketIO library"
SECTION = "libs" 
LICENSE = "CLOSED"
LIC_FILES_CHKSUM = ""

CONTROLLER = "EAGLE"

SRCBRANCH = "master"
SRCTAG = "1.6.1"
SRC_URI = "gitsm://github.com/socketio/socket.io-client-cpp.git;protocol=https;tag=${SRCTAG}"

PV = "1.0"

SRC_URI += " \
    file://0001-update-CMake-to-build-dynamic-SocketIO-lib.patch \
    file://0001-update-transport-connection-to-use-io_service.patch \
"

inherit cmake

DEPENDS = "uamqp curl avahi libusb boost"
RDEPENDS_${PN} = "boost"

prefix="/usr"

FILES_${PN} += " \
    ${prefix}/lib/* \
    ${prefix}/bin/* \
    ${includedir}/* \
" 

S = "${WORKDIR}/git"

INSANE_SKIP_${PN} = "dev-so"

# native yocto patch manager [quilt, git am , patch] look at git indexes
# for applying patches these use git indexes
# this fails in the context of a repo having submodules
# In such a case the git indexes of root repo is read and indexes not found 
# while applying patches to submodules
# Thus we override the do_patch hook to apply patches to submodules
do_patch() {
    cd ${S}
    git am ${WORKDIR}/0001-update-CMake-to-build-dynamic-SocketIO-lib.patch
             
    cd ${S}/lib/websocketpp
    git am  ${WORKDIR}/0001-update-transport-connection-to-use-io_service.patch
}