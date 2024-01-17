# Recipe created by recipetool
# This is the basis of a recipe and may need further editing in order to be fully functional.
# (Feel free to remove these comments when editing.)

SUMMARY = "HTTP transport for Azure IoT device SDK"
HOMEPAGE = "https://github.com/Azure/azure-iot-sdk-node#readme"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "npm://registry.npmjs.org/;name=azure-iot-device-http;version=${PV};noverify=1"

NPM_SHRINKWRAP := "${THISDIR}/${PN}/npm-shrinkwrap.json"
NPM_LOCKDOWN := "${THISDIR}/${PN}/lockdown.json"

inherit npm

# Must be set after inherit npm since that itself sets S
S = "${WORKDIR}/npmpkg"

npm_do_compile() {
    # Clean old node_modules, dist folder if existing before new install because not done by the clean step
    rm -rf node_modules/ dist/

    # Coming from original npm.bbclass but not sure if it is needed - to be investigate and cleaned if needed
    # Copy in any additionally fetched modules
    if [ -d ${WORKDIR}/node_modules ] ; then
        cp -a ${WORKDIR}/node_modules ${S}/
    fi
    # changing the home directory to the working directory, the .npmrc will
    # be created in this directory
    export HOME=${WORKDIR}

    npm set cache ${WORKDIR}/npm_cache
    # clear cache before every build
    npm cache clear --force

    # Install pkg into ${S}
    npm install
}
