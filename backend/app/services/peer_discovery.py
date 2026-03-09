"""Peer Discovery Service — Automatic peer machine detection via mDNS/zeroconf.

Automatically discovers peer machines on the local network using mDNS/zeroconf.
When a peer is discovered, automatically updates the machine identity service
with the peer's host address.

This enables zero-configuration dual-PC deployments where machines automatically
find each other on the network.
"""
import asyncio
import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)

# Service type for mDNS discovery
MDNS_SERVICE_TYPE = "_elite-trading._tcp.local."


class PeerDiscoveryService:
    """Discovers peer machines using mDNS/zeroconf.

    Broadcasts this machine's presence and listens for peer announcements.
    When a peer is discovered, automatically updates machine identity configuration.
    """

    def __init__(self):
        """Initialize peer discovery service."""
        self._running: bool = False
        self._zeroconf = None
        self._browser = None
        self._service_info = None
        self._discovery_enabled: bool = False

    async def start(self) -> None:
        """Start mDNS peer discovery.

        Attempts to import zeroconf library and start discovery.
        If zeroconf is not available, logs a warning and continues without discovery.
        """
        if self._running:
            logger.warning("PeerDiscovery: already running")
            return

        # Check if discovery is enabled in settings
        try:
            from app.services.settings_service import get_settings_by_category
            deployment_settings = get_settings_by_category("deployment")
            self._discovery_enabled = deployment_settings.get("autoDiscoverPeers", False)
        except Exception:
            self._discovery_enabled = False

        if not self._discovery_enabled:
            logger.info("PeerDiscovery: auto-discovery disabled in settings")
            return

        # Try to import zeroconf
        try:
            from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
        except ImportError:
            logger.warning(
                "PeerDiscovery: zeroconf library not installed. "
                "Install with 'pip install zeroconf' to enable auto-discovery. "
                "Falling back to manual peer configuration."
            )
            return

        try:
            self._running = True

            # Get machine identity to determine our role
            from app.services.machine_identity import get_machine_identity
            machine_identity = get_machine_identity()

            # Create zeroconf instance
            self._zeroconf = Zeroconf()

            # Register our service
            await self._register_service(machine_identity)

            # Start browsing for peers
            self._browser = ServiceBrowser(
                self._zeroconf,
                MDNS_SERVICE_TYPE,
                handlers=[self._on_service_state_change]
            )

            logger.info(
                "PeerDiscovery: started mDNS discovery (role=%s, service=%s)",
                machine_identity.machine_role,
                MDNS_SERVICE_TYPE
            )

        except Exception as e:
            logger.exception("PeerDiscovery: failed to start: %s", e)
            self._running = False
            await self.stop()

    async def _register_service(self, machine_identity) -> None:
        """Register this machine as a discoverable service."""
        try:
            from zeroconf import ServiceInfo

            # Get local IP address
            local_ip = self._get_local_ip()
            if not local_ip:
                logger.warning("PeerDiscovery: could not determine local IP address")
                return

            # Create service name with machine role
            service_name = f"{machine_identity.machine_id}._elite-trading._tcp.local."

            # Service properties
            properties = {
                "role": machine_identity.machine_role.encode(),
                "deployment_mode": machine_identity.deployment_mode.encode(),
                "machine_id": machine_identity.machine_id.encode(),
            }

            # Register service on port 8000 (FastAPI default)
            self._service_info = ServiceInfo(
                MDNS_SERVICE_TYPE,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=8000,
                properties=properties,
            )

            self._zeroconf.register_service(self._service_info)
            logger.info(
                "PeerDiscovery: registered service %s at %s:8000",
                service_name,
                local_ip
            )

        except Exception as e:
            logger.exception("PeerDiscovery: failed to register service: %s", e)

    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address for this machine."""
        try:
            # Connect to a public DNS server to determine local IP
            # This doesn't actually send data, just determines routing
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            # Fallback to hostname resolution
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return None

    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Handle service state changes (added/removed/updated)."""
        try:
            from zeroconf import ServiceStateChange

            if state_change == ServiceStateChange.Added:
                asyncio.create_task(self._on_service_added(zeroconf, service_type, name))
            elif state_change == ServiceStateChange.Removed:
                logger.info("PeerDiscovery: service removed: %s", name)

        except Exception as e:
            logger.exception("PeerDiscovery: error handling service state change: %s", e)

    async def _on_service_added(self, zeroconf, service_type, name):
        """Handle discovery of a new peer service."""
        try:
            from zeroconf import ServiceInfo

            # Get service info
            info = zeroconf.get_service_info(service_type, name)
            if not info:
                return

            # Parse service properties
            props = info.properties or {}
            peer_role = props.get(b"role", b"").decode()
            peer_machine_id = props.get(b"machine_id", b"").decode()

            # Get peer IP address
            if info.addresses:
                peer_ip = socket.inet_ntoa(info.addresses[0])
            else:
                return

            logger.info(
                "PeerDiscovery: discovered peer %s (role=%s) at %s:%d",
                peer_machine_id,
                peer_role,
                peer_ip,
                info.port
            )

            # Update machine identity with discovered peer
            from app.services.machine_identity import get_machine_identity
            machine_identity = get_machine_identity()

            # Only update if we don't have a peer configured
            # and the discovered peer has a complementary role
            if not machine_identity.peer_host:
                if self._is_complementary_role(machine_identity.machine_role, peer_role):
                    await self._configure_discovered_peer(peer_ip, peer_role)

        except Exception as e:
            logger.exception("PeerDiscovery: error processing discovered service: %s", e)

    def _is_complementary_role(self, our_role: str, peer_role: str) -> bool:
        """Check if peer role complements our role."""
        # PC1 pairs with PC2, and vice versa
        if our_role == "pc1" and peer_role == "pc2":
            return True
        if our_role == "pc2" and peer_role == "pc1":
            return True
        return False

    async def _configure_discovered_peer(self, peer_ip: str, peer_role: str) -> None:
        """Configure discovered peer in settings."""
        try:
            from app.services.settings_service import get_settings_service

            settings_service = get_settings_service()

            # Update deployment settings with discovered peer
            await settings_service.update_setting("deployment", "peerMachineHost", peer_ip)
            await settings_service.update_setting("deployment", "peerMachineRole", peer_role)
            await settings_service.update_setting("deployment", "deploymentMode", "dual_pc")

            logger.info(
                "PeerDiscovery: auto-configured peer %s (role=%s) - restarting required",
                peer_ip,
                peer_role
            )

            # Broadcast discovery event
            try:
                from app.websocket_manager import broadcast_ws
                payload = {
                    "type": "peer_discovered",
                    "peer_host": peer_ip,
                    "peer_role": peer_role,
                    "auto_configured": True,
                }
                asyncio.create_task(broadcast_ws("machine_status", payload))
            except Exception:
                pass

        except Exception as e:
            logger.exception("PeerDiscovery: failed to configure discovered peer: %s", e)

    async def stop(self) -> None:
        """Stop mDNS peer discovery."""
        self._running = False

        try:
            if self._browser:
                self._browser.cancel()
                self._browser = None

            if self._service_info and self._zeroconf:
                self._zeroconf.unregister_service(self._service_info)
                self._service_info = None

            if self._zeroconf:
                self._zeroconf.close()
                self._zeroconf = None

            logger.info("PeerDiscovery: stopped")

        except Exception as e:
            logger.exception("PeerDiscovery: error during shutdown: %s", e)


# Module-level singleton
_peer_discovery: Optional[PeerDiscoveryService] = None


def get_peer_discovery() -> PeerDiscoveryService:
    """Get or create the singleton PeerDiscoveryService.

    Returns:
        PeerDiscoveryService: The singleton instance
    """
    global _peer_discovery
    if _peer_discovery is None:
        _peer_discovery = PeerDiscoveryService()
    return _peer_discovery
