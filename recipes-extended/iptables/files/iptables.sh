#!/bin/sh
# Script to configure firewall through iptables

THIS="$0: "
#FPM: IPT=/sbin/iptables
IPT=/usr/sbin/iptables

#===================================================
# Checks
#===================================================
echo "${THIS}Checking system..."
if [ -e /proc/net/ip_tables_matches ]; then
    echo "${THIS}Kernel has netfilter installed..."
else
    echo "${THIS}Kernel has no netfilter installed!"
    exit 1
fi

if [ -e $IPT ]; then
    echo "${THIS}$($IPT --version)"
else
    echo "${THIS}iptables is missing!!"
    exit 1
fi

# Hach Controller Networking Bus (HCNB) config file (to enable/disable HCNB)
FILE_CONFIG_HCNB="/mnt/fcc/set/hcnb"
if [ -r $FILE_CONFIG_HCNB ]; then
    #echo "${THIS}File $FILE_CONFIG_HCNB does exist."
    HCNB_ENABLED=`cat $FILE_CONFIG_HCNB`
    echo "${THIS}File $FILE_CONFIG_HCNB contains: $HCNB_ENABLED"

    if [ "$HCNB_ENABLED" == "1" ]; then
    
        # HCNB config file (to set default HCNB network interface name)
        FILE_CONFIG_HCNB_INTERFACE="/mnt/fcc/set/hcnb_interface"
        if [ -r $FILE_CONFIG_HCNB_INTERFACE ]; then
            #echo "${THIS}File $FILE_CONFIG_HCNB_INTERFACE does exist."
            HCNB_INTERFACE=`cat $FILE_CONFIG_HCNB_INTERFACE`
            echo "${THIS}File $FILE_CONFIG_HCNB_INTERFACE contains: $HCNB_INTERFACE"
	         if [ -z $HCNB_INTERFACE ]; then
	            #echo "${THIS}File $FILE_CONFIG_HCNB_INTERFACE is empty."
	            # make setting for 'all' Interfaces
	            HCNB_INTERFACE="+"
	            echo "${THIS}Variable HCNB_INTERFACE now contains: $HCNB_INTERFACE"
	         fi
        else
            echo "File $FILE_CONFIG_HCNB_INTERFACE does not exist therefore we use setting with default value"
            # make setting for 'all' Interfaces
            HCNB_INTERFACE="+"
        fi
        

    
        # HCNB config file (to set default HCNB network port number)
        FILE_CONFIG_HCNB_PORT="/mnt/fcc/set/hcnb_port"
        if [ -r $FILE_CONFIG_HCNB_PORT ]; then
            #echo "${THIS}File $FILE_CONFIG_HCNB_PORT does exist."
            HCNB_PORT=`cat $FILE_CONFIG_HCNB_PORT`
        else
            echo "File $FILE_CONFIG_HCNB_PORT does not exist therefore we use setting with default value"
            HCNB_PORT=5445
        fi
        echo "${THIS}File $FILE_CONFIG_HCNB_PORT contains: $HCNB_PORT"
    fi
else
    #echo "${THIS}File $FILE_CONFIG_HCNB does not exist."
    HCNB_ENABLED=0
fi

#==================================================
# Add general rules
#==================================================
echo "${THIS}Adding general rules..."

# Clear INPUT, OUTPUT, FORWARD chains
$IPT -F
$IPT -X
$IPT -Z

# We consider that the controller itself is secure, so processes can communicate internally via localhost interface (e.g. connman for DNS caching)
$IPT -A INPUT  -i lo -j ACCEPT
$IPT -A OUTPUT -o lo -j ACCEPT

# Set general policies
$IPT -P INPUT DROP
$IPT -P OUTPUT DROP
$IPT -P FORWARD DROP

TETHERING_FILE_FLAG="/media/persistent/system/sharenet/tethering"
LANSERVER_FILE_FLAG="/media/persistent/system/sharenet/lanserver"
# Allow DHCP server communications when LAN server is enabled
if [ -e "${LANSERVER_FILE_FLAG}" ]; then
    $IPT -A INPUT -p udp --dport 67 -j ACCEPT
    $IPT -A OUTPUT -p udp --sport 67 -j ACCEPT
fi

# Allow DHCP server communications and DNS requests when tethering is enabled
if [ -e "${TETHERING_FILE_FLAG}" ]; then
    $IPT -A INPUT -p udp --dport 67 -j ACCEPT
    $IPT -A OUTPUT -p udp --sport 67 -j ACCEPT

    $IPT -A INPUT -p udp --dport 53 -j ACCEPT
    $IPT -A OUTPUT -p udp --sport 53 -j ACCEPT
fi

# First packet has to be TCP SYN
$IPT -A INPUT -p tcp ! --syn -m state --state NEW -j DROP

# Drop spoofed packets
$IPT -A INPUT -s 127.0.0.0/8 -j DROP
if [ "$HCNB_ENABLED" == "1" ]; then
    echo "no drop rules for multicast to make MDNS possible"
else
    $IPT -A INPUT -s 224.0.0.0/4 -j DROP
    $IPT -A INPUT -d 224.0.0.0/4 -j DROP
fi
$IPT -A INPUT -s 240.0.0.0/5 -j DROP
$IPT -A INPUT -d 240.0.0.0/5 -j DROP
$IPT -A INPUT -s 0.0.0.0/8 -j DROP
$IPT -A INPUT -d 0.0.0.0/8 -j DROP
$IPT -A INPUT -d 239.255.255.0/24 -j DROP
$IPT -A INPUT -d 255.255.255.255 -j DROP

# ICMP smurf attack + rate limit the rest
$IPT -A INPUT -p icmp --icmp-type address-mask-request -j DROP
$IPT -A INPUT -p icmp --icmp-type timestamp-request -j DROP
$IPT -A INPUT -p icmp --icmp-type router-solicitation -j DROP
$IPT -A INPUT -p icmp -m limit --limit 2/second -j ACCEPT

# Drop fragments
$IPT -A INPUT -f -j DROP

# Drop XMAS packets
$IPT -A INPUT -p tcp --tcp-flags ALL ALL -j DROP

# Drop NULL packets
$IPT -A INPUT -p tcp --tcp-flags ALL NONE -j DROP

# Stateful inspection: Accept all packets that are part of an established/related connection
$IPT -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Enable DNS
$IPT -A OUTPUT -p udp --dport 53 -j ACCEPT
$IPT -A INPUT -p udp --sport 53 -j ACCEPT
$IPT -A OUTPUT -p udp --sport 53 -j ACCEPT
$IPT -A INPUT -p udp --dport 53 -j ACCEPT
$IPT -A FORWARD -p udp --dport 53 -j ACCEPT
$IPT -A FORWARD -p udp --sport 53 -j ACCEPT

# Enable DHCP
$IPT -A INPUT -p udp --sport 68 -j ACCEPT
$IPT -A OUTPUT -p udp --dport 68 -j ACCEPT

# Allow DHCP traffic for other devices in chaining mode
$IPT -A FORWARD -p udp --sport 68 -j ACCEPT
$IPT -A FORWARD -p udp --dport 68 -j ACCEPT

# Enable ping
$IPT -A INPUT -p icmp --icmp-type echo-request -j ACCEPT     #Allowed ping from PC to FPM
$IPT -A OUTPUT -p icmp --icmp-type echo-reply -j ACCEPT      #Allowed ping from PC to FPM
$IPT -A OUTPUT -p icmp --icmp-type echo-request -j ACCEPT    #Allowed ping from FPM to PC
$IPT -A INPUT -p icmp --icmp-type echo-reply -j ACCEPT       #Allowed ping from FPM to PC
$IPT -A FORWARD -p icmp --icmp-type echo-request -j ACCEPT
$IPT -A FORWARD -p icmp --icmp-type echo-reply -j ACCEPT

# Enable Outgoing HTTP traffic (Wget)
$IPT -A INPUT -p tcp --sport 80 -j ACCEPT
$IPT -A OUTPUT -p tcp --dport 80 -j ACCEPT

# Enable Forwarding HTTP traffic
$IPT -A FORWARD -p tcp --dport 80 -j ACCEPT
$IPT -A FORWARD -p tcp --sport 80 -j ACCEPT

# Enable SSH
$IPT -A INPUT -p tcp --dport 22 -j ACCEPT    #communication start from PC to FPM, data send to PC
$IPT -A OUTPUT -p tcp --sport 22 -j ACCEPT   #communication start from PC to FPM, data send to FPM
$IPT -A FORWARD -p tcp --dport 22 -j ACCEPT
$IPT -A FORWARD -p tcp --sport 22 -j ACCEPT

# Enable NTP
$IPT -A OUTPUT -p udp --dport 123 -j ACCEPT #Both directions and both communication start location are nessasary
$IPT -A OUTPUT -p udp --sport 123 -j ACCEPT
$IPT -A INPUT -p udp --dport 123 -j ACCEPT
$IPT -A FORWARD -p udp --dport 123 -j ACCEPT
$IPT -A FORWARD -p udp --sport 123 -j ACCEPT

# Enable AMQPS
$IPT -A OUTPUT -p tcp --dport 5671 -j ACCEPT #port 5671 is for AMQPS
$IPT -A INPUT -p tcp --sport 5671 -j ACCEPT
$IPT -A FORWARD -p tcp --dport 5671 -j ACCEPT
$IPT -A FORWARD -p tcp --sport 5671 -j ACCEPT

# Enable OpenVPN
$IPT -A INPUT  -i tun+ -j ACCEPT
$IPT -A OUTPUT -p udp --dport 1194 -j ACCEPT
$IPT -A FORWARD -p udp --dport 1194 -j ACCEPT
$IPT -A FORWARD -p udp --sport 1194 -j ACCEPT

# Enable Outgoing HTTPS traffic (for update)
$IPT -A INPUT -p tcp --sport 443 -j ACCEPT
$IPT -A OUTPUT -p tcp --dport 443 -j ACCEPT

# Enable Forwarding HTTPS traffic
$IPT -A FORWARD -p tcp --dport 443 -j ACCEPT
$IPT -A FORWARD -p tcp --sport 443 -j ACCEPT

# Enable SysLog
$IPT -A OUTPUT -p udp --dport 514 -j ACCEPT
$IPT -A INPUT -p udp --dport 513 -j ACCEPT
$IPT -A FORWARD -p udp --dport 514 -j ACCEPT

if [ "$HCNB_ENABLED" == "1" ]; then
    # Enable Hach Controller Networking Bus (HCNB) Protokoll
    $IPT -A OUTPUT -p tcp -o "$HCNB_INTERFACE" --dport $HCNB_PORT -j ACCEPT
    $IPT -A INPUT -p tcp -i "$HCNB_INTERFACE" --dport $HCNB_PORT -j ACCEPT
    $IPT -A OUTPUT -p tcp -o "$HCNB_INTERFACE" --sport $HCNB_PORT -j ACCEPT

    # Allow forwarding HCNB communication to make it possible to build an HCNB
    # network out of multiple controllers connected together in chaining mode.
    $IPT -A FORWARD -p tcp --dport $HCNB_PORT -j ACCEPT
    $IPT -A FORWARD -p tcp --sport $HCNB_PORT -j ACCEPT

    # Enable MDNS (used by HCNB)
    $IPT -A OUTPUT -p udp -o "$HCNB_INTERFACE" --dport 5353 -j ACCEPT
    $IPT -A INPUT -p udp -i "$HCNB_INTERFACE" --dport 5353 -j ACCEPT
    $IPT -A FORWARD -p udp --dport 5353 -j ACCEPT
    $IPT -A FORWARD -p udp --sport 5353 -j ACCEPT
else
    echo "File $FILE_CONFIG_HCNB does not exist. Do not use rules for HCNB."
fi

# Enable Incomming Modbus TCP
$IPT -A INPUT -p tcp -i br0 --dport 502 -j ACCEPT
$IPT -A OUTPUT -p tcp -o br0 --sport 502 -j ACCEPT
$IPT -A INPUT -p tcp -i wlan0 --dport 502 -j ACCEPT
$IPT -A OUTPUT -p tcp -o wlan0 --sport 502 -j ACCEPT

# Enable outgoing Modbus TCP
$IPT -A INPUT -p tcp -i br0 --sport 502 -j ACCEPT
$IPT -A OUTPUT -p tcp -o br0 --dport 502 -j ACCEPT
$IPT -A INPUT -p tcp -i wlan0 --sport 502 -j ACCEPT
$IPT -A OUTPUT -p tcp -o wlan0 --dport 502 -j ACCEPT

# Allow to chain Modbus TCP traffic through multiple devices
$IPT -A FORWARD -p tcp -i br0 --dport 502 -j ACCEPT
$IPT -A FORWARD -p tcp -i br0 --sport 502 -j ACCEPT
$IPT -A FORWARD -p tcp -i wlan0 --dport 502 -j ACCEPT
$IPT -A FORWARD -p tcp -i wlan0 --sport 502 -j ACCEPT

DEV_FILE_FLAG="/media/persistent/development"
IPTABLES_DEVELOPER_SCRIPT="/usr/local/bin/iptables_dev.sh"
if [ -e "${DEV_FILE_FLAG}" ] && [ -x "${IPTABLES_DEVELOPER_SCRIPT}" ]; then
    ${IPTABLES_DEVELOPER_SCRIPT}
fi

# Provide reject replies to mask the presence of active iptables rules
$IPT -A INPUT -p tcp -j REJECT --reject-with tcp-reset
$IPT -A INPUT -p udp -j REJECT --reject-with icmp-port-unreachable

exit 0
