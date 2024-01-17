# the package obex-profiles has "icu" as dependencies
# The librairy "libicudata57" has a size of 25MB
# Remove this unused package to not embeds in image the library libicudata57
PACKAGECONFIG_remove = "obex-profiles"
