# This file is to include extra elements/steps.
# These steps/tasks could not be integrated into general/natural 
# yocto provided recipe layers

# this symbolic link creation is necessary
# For having frontend working when it is packaged from a window machine
add_symbolic_links() {
    cd ${IMAGE_ROOTFS}/lib
    ln -snf "libz.so.1" "libz.so"
}

ROOTFS_POSTPROCESS_COMMAND += "add_symbolic_links; "
