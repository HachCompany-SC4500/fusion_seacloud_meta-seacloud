DESCRIPTION = "wt (WebToolKit) library" 
SECTION = "libs" 
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://${S}/LICENSE;md5=35b7527e053cc3586c91a877183dacad"
PR = "r0" 

DEPENDS = "openssl boost"

# This git commit corresponds to the tag of the release wt 4.2.0
SRC_URI = "git://github.com/emweb/wt.git"
SRCREV = "d428c3065becb1a63f92099e8e165e555be3f36a"
S = "${WORKDIR}/git"

SRC_URI += "file://bootstrap.tar.bz2"

inherit pkgconfig cmake 

EXTRA_OECMAKE = " \
	-DSHARED_LIBS:BOOL=OFF \
	-DENABLE_EXT:BOOL=OFF \
	-DENABLE_FIREBIRD:BOOL=OFF \
	-DENABLE_HARU:BOOL=OFF \
	-DENABLE_LIBWTDBO:BOOL=OFF \
	-DENABLE_LIBWTTEST:BOOL=OFF \
	-DENABLE_MYSQL:BOOL=OFF \
	-DENABLE_OPENGL:BOOL=OFF \
	-DENABLE_PANGO:BOOL=OFF \
	-DENABLE_POSTGRES:BOOL=OFF \
	-DENABLE_QT4:BOOL=OFF \
	-DENABLE_SQLITE:BOOL=OFF \
	-DENABLE_SSL:BOOL=ON \
	-DBUILD_EXAMPLES=ON \
	-DBUILD_TESTS=OFF \
	-DCMAKE_BUILD_TYPE=MinSizeRel \
	-DCMAKE_CXX_FLAGS_MINSIZEREL="-Os -DNDEBUG" \
	-DCMAKE_C_FLAGS_MINSIZEREL="-Os -DNDEBUG" \
	-DDEBUG=ON \
	-DCONNECTOR_FCGI=OFF \
	-DHTTP_WITH_ZLIB=ON \
	-DINSTALL_EXAMPLES=OFF \
	-DINSTALL_FINDWT_CMAKE_FILE=OFF \
	-DSHARED_LIBS=OFF \
	-DINSTALL_RESOURCES=ON \
	-DMULTI_THREADED=ON \
	-DUSE_SQLITE3_BDB=OFF \
	-DUSE_SYSTEM_IBPP=OFF \
	-DUSE_SYSTEM_SQLITE3=OFF \
	-DWEBGROUP=apache \
	-DWEBUSER=apache \
	-DWTHTTP_CONFIGURATION="/etc/wt/wthttpd" \
	-DWT_BOOST_DISCOVERY=OFF \
	-DWT_NO_BOOST_RANDOM=OFF \	
	-DWT_NO_STD_LOCALE=OFF \
	-DWT_NO_STD_WSTRING=OFF \
	-DWT_SKIA_OLD=OFF \
"

TARGET_CFLAGS += "-fPIC"
TARGET_LDFLAGS += "-fvisibility=hidden -fvisibility-inlines-hidden -ffunction-sections -fdata-sections -rdynamic"

do_install (){
	arm-tdx-linux-gnueabi-strip -S ${S}/../build/src/libwt.a
	arm-tdx-linux-gnueabi-strip -S ${S}/../build/src/http/libwthttp.a
	cp -r ${S}/../bootstrap ${S}/resources/themes/
	cmake_do_install
}

FILES_${PN} = "\
    /usr/lib/* \
    /usr/share/* \
    /etc/wt/* \
"
