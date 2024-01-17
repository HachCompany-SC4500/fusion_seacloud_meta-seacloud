FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

# do_compile_prepend supports forward feature to support GCC plugins
# it takes the forward changes setting gcc-cross-arm's checksum and config_args
# to be same across builds of individual sys_components
# THIS WAS NEEDED TO SUPPORT SECURE COMPILATION FLAGS IN LINUX_TORADEX
# the function patches/modifies the gcc-cross's configuration args to be constant
# reference http://git.yoctoproject.org/cgit/cgit.cgi/poky/tree/meta/recipes-devtools/gcc/gcc-cross.inc
# the modifications are avilable as a part of the latest open-embedded layer
# this  override can be removed once migrating to the latest open-embedded layer
do_compile_prepend() {
	export CC="${BUILD_CC}"
	export AR_FOR_TARGET="${TARGET_SYS}-ar"
	export RANLIB_FOR_TARGET="${TARGET_SYS}-ranlib"
	export LD_FOR_TARGET="${TARGET_SYS}-ld"
	export NM_FOR_TARGET="${TARGET_SYS}-nm"
	export CC_FOR_TARGET="${CCACHE} ${TARGET_SYS}-gcc"
	export CFLAGS_FOR_TARGET="${TARGET_CFLAGS}"
	export CPPFLAGS_FOR_TARGET="${TARGET_CPPFLAGS}"
	export CXXFLAGS_FOR_TARGET="${TARGET_CXXFLAGS}"
	export LDFLAGS_FOR_TARGET="${TARGET_LDFLAGS}"

	# Prevent native/host sysroot path from being used in configargs.h header,
	# as it will be rewritten when used by other sysroots preventing support
	# for gcc plugins
	oe_runmake configure-gcc
	sed -i 's@${STAGING_DIR_TARGET}@/host@g' ${B}/gcc/configargs.h
	sed -i 's@${STAGING_DIR_HOST}@/host@g' ${B}/gcc/configargs.h

	# Prevent sysroot/workdir paths from being used in checksum-options.
	# checksum-options is used to generate a checksum which is embedded into
	# the output binary.
	oe_runmake TARGET-gcc=checksum-options all-gcc
	sed -i 's@${DEBUG_PREFIX_MAP}@@g' ${B}/gcc/checksum-options
	sed -i 's@${STAGING_DIR_HOST}@/host@g' ${B}/gcc/checksum-options
}