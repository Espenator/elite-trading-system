"""Machine Identity Service — Deterministic machine detection and role assignment.

Determines which machine we're running on and what deployment mode is active.

Priority order for machine role detection:
    1. Saved settings in DuckDB (user/system choice)
    2. Environment variable override (MACHINE_ROLE)
    3. Hostname detection (ESPENMAIN → pc1, ProfitTrader → pc2)
    4. Safe fallback (standalone mode)

Part of machine-awareness architecture (#issue)
"""
import asyncio
import logging
import os
import socket
from typing import Any, Dict, Literal, Optional

logger = logging.getLogger(__name__)

MachineRole = Literal["pc1", "pc2", "standalone"]
DeploymentMode = Literal["single_pc", "dual_pc"]


class MachineIdentityService:
    """Determines which machine we're running on and what mode we're in.

    This service provides a single source of truth for:
    - Machine identity (which PC is this?)
    - Machine role (PC1/primary, PC2/secondary, or standalone)
    - Deployment mode (single-PC or dual-PC)
    - Peer availability status
    - Fallback mode activation
    """

    def __init__(self):
        """Initialize machine identity with auto-detection."""
        self.machine_id: str = ""
        self.machine_name: str = ""
        self.machine_role: MachineRole = "standalone"
        self.deployment_mode: DeploymentMode = "single_pc"
        self.peer_host: str = ""
        self.peer_online: bool = False
        self.fallback_mode: bool = False
        self.gpu_enabled: bool = False
        self.gpu_device_index: int = 0

        # Detection method used (for debugging)
        self._detection_method: str = ""

        # Background health check task
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval: int = 30  # seconds
        self._running: bool = False

        # Track previous state for change detection
        self._prev_peer_online: bool = False
        self._prev_fallback_mode: bool = False

        self._detect()

    def _detect(self) -> None:
        """Priority: saved settings > env override > hostname detection > safe fallback."""
        try:
            from app.services.settings_service import get_settings_by_category
            machine_settings = get_settings_by_category("machine")
            deployment_settings = get_settings_by_category("deployment")
        except Exception as e:
            logger.warning("Failed to load settings for machine detection: %s", e)
            machine_settings = {}
            deployment_settings = {}

        # Detect machine role
        self._detect_machine_role(machine_settings)

        # Detect deployment mode
        self._detect_deployment_mode(machine_settings, deployment_settings)

        # GPU configuration
        self.gpu_enabled = machine_settings.get("gpuEnabled", True)
        self.gpu_device_index = machine_settings.get("gpuDeviceIndex", 0)

    def _detect_machine_role(self, machine_settings: Dict[str, Any]) -> None:
        """Detect machine role using priority cascade."""
        # 1. Check saved settings
        saved_role = machine_settings.get("machineRole", "auto")
        if saved_role in ("pc1", "pc2", "standalone"):
            self.machine_role = saved_role
            self.machine_id = machine_settings.get("machineId", socket.gethostname())
            self.machine_name = machine_settings.get("machineName", self.machine_id)
            self._detection_method = "saved_settings"
            logger.info(
                "MachineIdentity: using saved role=%s (machine_id=%s)",
                saved_role, self.machine_id
            )
            return

        # 2. Check environment override
        env_role = os.getenv("MACHINE_ROLE", "").lower()
        if env_role in ("pc1", "pc2", "standalone"):
            self.machine_role = env_role
            self.machine_id = os.getenv("MACHINE_ID", socket.gethostname())
            self.machine_name = os.getenv("MACHINE_NAME", self.machine_id)
            self._detection_method = "environment_variable"
            logger.info(
                "MachineIdentity: using env MACHINE_ROLE=%s (machine_id=%s)",
                env_role, self.machine_id
            )
            return

        # 3. Hostname detection
        if machine_settings.get("autoDetectHostname", True):
            self._detect_by_hostname(machine_settings)
        else:
            # Fallback to standalone if auto-detect is disabled
            self.machine_role = "standalone"
            self.machine_id = socket.gethostname()
            self.machine_name = self.machine_id
            self._detection_method = "disabled_auto_detect"
            logger.info(
                "MachineIdentity: auto-detect disabled → role=standalone (hostname=%s)",
                self.machine_id
            )

    def _detect_by_hostname(self, machine_settings: Dict[str, Any]) -> None:
        """Detect machine role from hostname."""
        hostname = socket.gethostname().upper()
        self.machine_id = hostname

        # Check for hostname override
        override = machine_settings.get("hostnameOverride", "").upper()
        if override:
            hostname = override
            logger.info("MachineIdentity: using hostname override=%s", override)

        # Hostname → role mapping
        if "ESPENMAIN" in hostname:
            self.machine_role = "pc1"
            self.machine_name = "ESPENMAIN (Primary Intelligence Node)"
            self._detection_method = "hostname_detection"
            logger.info(
                "MachineIdentity: detected hostname=%s → role=pc1",
                self.machine_id
            )
        elif "PROFITTRADER" in hostname:
            self.machine_role = "pc2"
            self.machine_name = "ProfitTrader (Secondary Compute Node)"
            self._detection_method = "hostname_detection"
            logger.info(
                "MachineIdentity: detected hostname=%s → role=pc2",
                self.machine_id
            )
        else:
            self.machine_role = "standalone"
            self.machine_name = f"{self.machine_id} (Standalone)"
            self._detection_method = "hostname_unknown_fallback"
            logger.warning(
                "MachineIdentity: unknown hostname=%s → role=standalone (safe fallback)",
                self.machine_id
            )

    def _detect_deployment_mode(
        self,
        machine_settings: Dict[str, Any],
        deployment_settings: Dict[str, Any]
    ) -> None:
        """Detect deployment mode (single-PC vs dual-PC)."""
        # Check explicit deployment mode setting
        saved_mode = deployment_settings.get("deploymentMode", "auto")
        if saved_mode in ("single_pc", "dual_pc"):
            self.deployment_mode = saved_mode
            logger.info("MachineIdentity: using saved deployment_mode=%s", saved_mode)
        else:
            # Auto-detect based on peer configuration
            self.peer_host = deployment_settings.get("peerMachineHost", "").strip()

            # Also check legacy config settings for peer host
            if not self.peer_host:
                try:
                    from app.core.config import settings
                    self.peer_host = (settings.CLUSTER_PC2_HOST or "").strip()
                    if self.peer_host:
                        logger.info(
                            "MachineIdentity: using CLUSTER_PC2_HOST=%s for peer",
                            self.peer_host
                        )
                except Exception:
                    pass

            if self.peer_host:
                self.deployment_mode = "dual_pc"
                logger.info(
                    "MachineIdentity: detected deployment_mode=dual_pc (peer=%s)",
                    self.peer_host
                )
            else:
                self.deployment_mode = "single_pc"
                logger.info("MachineIdentity: detected deployment_mode=single_pc (no peer configured)")

    async def check_peer_online(self) -> bool:
        """Ping peer machine to check if it's reachable.

        Returns:
            bool: True if peer responds to health check, False otherwise
        """
        if not self.peer_host:
            self.peer_online = False
            self.fallback_mode = False
            return False

        import httpx

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"http://{self.peer_host}:8000/api/v1/health")
                self.peer_online = resp.status_code == 200
        except Exception as e:
            logger.debug("Peer health check failed: %s", e)
            self.peer_online = False

        # Fallback mode = dual-PC deployment but peer is offline
        prev_fallback = self.fallback_mode
        self.fallback_mode = (
            self.deployment_mode == "dual_pc" and not self.peer_online
        )

        # Detect state changes and broadcast events
        self._detect_and_broadcast_changes(prev_fallback)

        if self.fallback_mode:
            logger.warning(
                "MachineIdentity: FALLBACK MODE ACTIVE - peer %s is unreachable",
                self.peer_host
            )

        return self.peer_online

    def _detect_and_broadcast_changes(self, prev_fallback: bool) -> None:
        """Detect state changes and broadcast WebSocket events."""
        peer_changed = self._prev_peer_online != self.peer_online
        fallback_changed = prev_fallback != self.fallback_mode

        if peer_changed or fallback_changed:
            # Broadcast state change event
            self._broadcast_status_change(
                peer_changed=peer_changed,
                fallback_changed=fallback_changed
            )

            # Update previous state
            self._prev_peer_online = self.peer_online
            self._prev_fallback_mode = self.fallback_mode

            # Log important transitions
            if peer_changed:
                if self.peer_online:
                    logger.info("MachineIdentity: Peer %s is now ONLINE", self.peer_host)
                else:
                    logger.warning("MachineIdentity: Peer %s is now OFFLINE", self.peer_host)

            if fallback_changed:
                if self.fallback_mode:
                    logger.warning("MachineIdentity: Entering FALLBACK MODE")
                else:
                    logger.info("MachineIdentity: Exiting FALLBACK MODE - dual-PC mode restored")

    def _broadcast_status_change(self, peer_changed: bool, fallback_changed: bool) -> None:
        """Broadcast machine status change via WebSocket."""
        try:
            from app.websocket_manager import broadcast_ws

            payload = {
                "type": "machine_status_change",
                "machine_id": self.machine_id,
                "machine_role": self.machine_role,
                "deployment_mode": self.deployment_mode,
                "peer_online": self.peer_online,
                "fallback_mode": self.fallback_mode,
                "peer_changed": peer_changed,
                "fallback_changed": fallback_changed,
                "timestamp": None,  # Will be added by broadcast_ws
            }

            # Non-blocking broadcast
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(broadcast_ws("machine_status", payload))
            except RuntimeError:
                # No event loop (startup or testing)
                logger.debug("No event loop available for WebSocket broadcast")

        except Exception as e:
            logger.debug("Failed to broadcast machine status change: %s", e)

    async def start_health_checks(self) -> None:
        """Start background peer health check loop.

        Only starts if in dual-PC mode with a peer configured.
        """
        if self._running:
            logger.warning("MachineIdentity: health check loop already running")
            return

        if self.deployment_mode != "dual_pc" or not self.peer_host:
            logger.info(
                "MachineIdentity: skipping health checks (mode=%s, peer=%s)",
                self.deployment_mode,
                self.peer_host or "none"
            )
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(
            "MachineIdentity: started background health checks for peer %s (interval=%ds)",
            self.peer_host,
            self._health_check_interval
        )

    async def stop_health_checks(self) -> None:
        """Stop background peer health check loop."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("MachineIdentity: stopped background health checks")

    async def _health_check_loop(self) -> None:
        """Background loop for periodic peer health checks."""
        # Initial delay before first check
        await asyncio.sleep(10)

        while self._running:
            try:
                await self.check_peer_online()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("MachineIdentity: error in health check loop: %s", e)

            # Wait for next check
            try:
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break

    def get_status(self) -> Dict[str, Any]:
        """Return current machine identity status.

        Returns:
            dict: Machine identity state including role, mode, and peer status
        """
        return {
            "machine_id": self.machine_id,
            "machine_name": self.machine_name,
            "machine_role": self.machine_role,
            "deployment_mode": self.deployment_mode,
            "peer_host": self.peer_host or None,
            "peer_online": self.peer_online,
            "fallback_mode": self.fallback_mode,
            "gpu_enabled": self.gpu_enabled,
            "gpu_device_index": self.gpu_device_index,
            "detection_method": self._detection_method,
        }

    def is_pc1(self) -> bool:
        """Check if this machine is PC1 (primary)."""
        return self.machine_role == "pc1"

    def is_pc2(self) -> bool:
        """Check if this machine is PC2 (secondary)."""
        return self.machine_role == "pc2"

    def is_standalone(self) -> bool:
        """Check if this machine is standalone."""
        return self.machine_role == "standalone"

    def is_dual_pc_mode(self) -> bool:
        """Check if system is configured for dual-PC deployment."""
        return self.deployment_mode == "dual_pc"

    def is_single_pc_mode(self) -> bool:
        """Check if system is configured for single-PC deployment."""
        return self.deployment_mode == "single_pc"

    def should_run_service(self, service_type: str) -> bool:
        """Determine if a service should run on this machine.

        Args:
            service_type: Type of service ("training", "inference", "execution", "intelligence")

        Returns:
            bool: True if service should run on this machine
        """
        try:
            from app.services.settings_service import get_settings_by_category
            deployment_settings = get_settings_by_category("deployment")
        except Exception:
            deployment_settings = {}

        affinity_mode = deployment_settings.get("serviceAffinityMode", "auto")

        if affinity_mode == "manual":
            # Check explicit manual settings
            service_key = f"run{service_type.capitalize()}Services"
            setting = deployment_settings.get(service_key, "auto")
            if setting == "yes":
                return True
            elif setting == "no":
                return False
            # Fall through to auto if setting is "auto"

        # Auto mode or manual fallback to auto
        if self.is_standalone():
            return True  # Standalone runs everything

        if self.is_single_pc_mode():
            return True  # Single-PC mode runs everything on one machine

        # Dual-PC mode auto affinity
        if self.fallback_mode:
            return True  # Fallback mode: run everything locally

        # Normal dual-PC distribution
        if service_type == "training":
            return self.is_pc2()  # Training prefers PC2
        elif service_type == "inference":
            return True  # Both can run inference
        elif service_type == "execution":
            return self.is_pc1()  # Execution on PC1 (has DuckDB)
        elif service_type == "intelligence":
            return self.is_pc1()  # Intelligence/orchestration on PC1

        return True  # Default: allow service


# Module-level singleton
_machine_identity: Optional[MachineIdentityService] = None


def get_machine_identity() -> MachineIdentityService:
    """Get or create the singleton MachineIdentityService.

    Returns:
        MachineIdentityService: The singleton instance
    """
    global _machine_identity
    if _machine_identity is None:
        _machine_identity = MachineIdentityService()
    return _machine_identity
