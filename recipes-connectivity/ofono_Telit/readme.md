# How to modify oFono for SeaCloud

The source code of Ofono is on the dedicated repository "Fusion_SeaCloud_ofono", the branch "patches_telit" includes the modifications added to ofono version to include the support of telit modems.

Dedicated seacloud recipe for ofono (meta-seacloud/recipes-connectivity/ofono_Telit)  refers to this repo. So modifications done on Ofono, have to be done on "Fusion_SeaCloud_ofono" repo then files "ofono_%.bb" and "ofono-git-version.patch" into meta-seacloud have to be updated accordingly.


## Method 1 - modify oFono using make command
    Prerequisites
    On Ubuntu 16.04, the following packages have to be installed: autoconf + dependencies and libtool + dependencies
    To install them, use the command # sudo synaptic

If not already done, git clone the repo "Fusion_SeaCloud_ofono" under a folder  (ie: oe-core/layers).

1. Go under "fusion_seacloud_ofono"
2. Checkout the branch "patches_telit"
3. Source the environment settings provided by "SeaCloud SDK" (command "# source  environment-setup-armv7at2hf-neon-angstrom-linux-gnueabi").
4. Run autoreconf with option --install to create the executable file "configure" :" # autoreconf --install"
5. Create the Makefile using the command "# ./configure --host=arm"
6. Build using make: "# make"
7. Test (copy new ofonod under the target, run it) and redo some modifications if needed
8. When the modifications are done, commit and push the files.
9. Update ofono recipe ofono_%.bb under "meta-seacloud/recipes-connectivity/ofono_Telit" to update the SHA1 of the SRCREV
10. Update the patch ofono-git-version.patch under "meta-seacloud/recipes-connectivity/ofono_Telit/files"  to change the SHA1
11. Now you can use bitbake to generate the package, the last modifications should be there.


## Method 2 - modify oFono using devtool
If not already done, git clone the repo "Fusion_SeaCloud_ofono" under OE-core/layers.
1. Use devtool to modify source code (see "Add a patch to a package - devtool") but do not apply a patch to the recipe !!! Here the idea is to modify the "seacloud_ofono" repo.
2. So report the modifications into "seacloud_ofono" repo, push them
3. Update ofono recipe ofono_%.bb under "meta-seacloud/recipes-connectivity/ofono_Telit" to update the SHA1 of the SRCREV
4. Update the patch ofono-git-version.patch under "meta-seacloud/recipes-connectivity/ofono_Telit/files"  to change the SHA1
5. Now you can use bitbake to generate the package, the last modifications should be there.