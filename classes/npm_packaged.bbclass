#
# !!! THIS BBCLASS IS A TEST TO HAVE A CLEANER RECIPE FOR NPM PACKAGES. IT IS CURRENTLY NOT WORKING PROPERLY SO IT IS KEPT HERE AS A DRAFT !!!
#


#
# This class targets nodejs applications that are packaged
#
# Note: For non packaged applications prefer standard npm.class
#
# do_clean
# * clean the dist folder
#
# do_compile
# * change HOME directory for .npmrc file
# * use developer mode
# * npm install
#
# do_install
# * npm pack
# * copy generated files in /usr/local/bin
#
# populate_packages_prepend
#

DEPENDS_prepend = "nodejs-native "
RDEPENDS_${PN}_prepend = "nodejs "

NPM_INSTALLDIR = "${D}${libdir}/node_modules/${PN}"

do_clean() {
    # Clean old node_modules folder if existing before new install
    rm -rf node_modules/
}

# Run in ${B} folder ( =${S} by default)
npm_packaged_do_compile() {

    # changing the home directory to the working directory, the .npmrc will
    # be created in this directory
    export HOME=${B}

    # clear cache before every build
    npm set cache ${B}/npm_cache
    npm cache clear --force

    # Install all modules into ${B}
    npm install -g
}

# Overwrite npm.bbclass populate_packages_prepend to avoid adding all packages for the node modules as dependencies at runtime
python populate_packages_prepend () {
    pass
}

EXPORT_FUNCTIONS do_compile

