# WireGuard Real VPN Mode

This build configures a real WireGuard interface and IPv4 full-tunnel NAT automatically when the runtime grants the container the required Linux networking privileges.

## Required runtime capabilities
- NET_ADMIN
- UDP exposure for the WireGuard listen port (default 51820/udp)
- IPv4 forwarding
- WireGuard kernel support on the host (or an environment that provides it)

The web panel uses TCP 5000. VPN traffic uses UDP 51820.

The application automatically:
- installs wireguard-tools/iproute2/iptables in the image
- generates server and client keypairs
- creates /etc/wireguard/wg0.conf
- enables IPv4 forwarding
- adds FORWARD rules
- adds MASQUERADE/NAT on the detected default uplink
- applies the interface with wg-quick
- disables expired clients automatically
- generates client .conf and QR codes

Important: application code cannot grant NET_ADMIN, privileged mode, or a host UDP port mapping if the hosting platform forbids them. If Stackdome does not expose these capabilities for the service, a real server-side WireGuard tunnel cannot be made operational only by changing Python code.
