#!/bin/sh

set -e

# List of users that for which access will not be removed over SSH.
# The list must be specified in the following format:
# "^username1:[|^username2:[|...]]" in which square braquets ('[' and ']')
# denote optional strings and "..." indicates the recursive nature of
# the pattern.
exceptions="^_fit:"

### Lock the bootloader console access
/usr/local/bin/uboot_shell_control.sh lock

### Remove access over SSH to all users except for those listed in 'exceptions'
home_list="$(grep -v "${exceptions}" /etc/passwd | cut -f 6 -d ':')"
for home in ${home_list}
do
    rm -f "${home}/.ssh/authorized_keys"
done

### Empty the list of users temporarily allowed to connect via SSH
/usr/sbin/groupmems --group ssh-allowed-tmp --purge

### Remove access over serial console to all users
sed -i 's/^\([^:]*\):[^:]*:/\1:*:/g' /etc/passwd
sed -i 's/^\([^:]*\):[^:]*:/\1:*:/g' /etc/shadow

### Enable all security features specified in the SSHD configuration file
cp -a /etc/ssh/sshd_config_prod /etc/ssh/sshd_config
cp -a /etc/ssh/sshd_config_prod /etc/ssh/sshd_config_readonly
