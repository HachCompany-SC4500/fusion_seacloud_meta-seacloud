#!/bin/sh
# Script to configure firewall through iptables for developers

IPT=/usr/sbin/iptables

printf "Applying developer IPTABLES rules"

# Log channel: only for test
#$IPT -N LOGGING
#$IPT -A INPUT -j LOGGING
#$IPT -A OUTPUT -j LOGGING
#$IPT -A LOGGING -j LOG --log-prefix "IPTables-Dropped: " --log-level 4
#$IPT -A LOGGING -j DROP

# GDB Remote debugging
$IPT -I INPUT -p tcp --dport 2345 -j ACCEPT
$IPT -I OUTPUT -p tcp --sport 2345 -j ACCEPT
$IPT -I FORWARD -p tcp --dport 2345 -j ACCEPT
$IPT -I FORWARD -p tcp --sport 2345 -j ACCEPT

# Allow remote connection to backend API
$IPT -I INPUT -p tcp --dport 3000 -j ACCEPT
$IPT -I OUTPUT -p tcp --sport 3000 -j ACCEPT
$IPT -I FORWARD -p tcp --dport 3000 -j ACCEPT
$IPT -I FORWARD -p tcp --sport 3000 -j ACCEPT

# Allow remote connection to backend Socket.IO
$IPT -I INPUT -p tcp --dport 3001 -j ACCEPT
$IPT -I OUTPUT -p tcp --sport 3001 -j ACCEPT
$IPT -I FORWARD -p tcp --dport 3001 -j ACCEPT
$IPT -I FORWARD -p tcp --sport 3001 -j ACCEPT

# Allow VNC connections
$IPT -I INPUT -p tcp --dport 5900 -j ACCEPT
$IPT -I OUTPUT -p tcp --sport 5900 -j ACCEPT
$IPT -I FORWARD -p tcp --dport 5900 -j ACCEPT
$IPT -I FORWARD -p tcp --sport 5900 -j ACCEPT

# Allow HTTP connection to SWUpdate webserver
$IPT -I INPUT -p tcp --dport 8080 -j ACCEPT
$IPT -I OUTPUT -p tcp --sport 8080 -j ACCEPT
$IPT -I FORWARD -p tcp --dport 8080 -j ACCEPT
$IPT -I FORWARD -p tcp --sport 8080 -j ACCEPT

printf "Developer IPTABLES rules applied"

exit 0
