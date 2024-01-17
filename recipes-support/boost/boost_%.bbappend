# locale is used by boost for translation
# this package has "icu" as dependencies
# The librairy "libicudata57" has a size of 25MB
# Remove this unused package to not embeds in image the library libicudata57
PACKAGECONFIG_remove = "locale"

