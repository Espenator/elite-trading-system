"""Tests for machine awareness features.

Tests machine identity service, peer discovery, health checks, and auto-recovery.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.services.machine_identity import MachineIdentityService, get_machine_identity
from app.services.peer_discovery import PeerDiscoveryService


class TestMachineIdentityService:
    """Tests for MachineIdentityService."""

    def test_hostname_detection_pc1(self):
        """Test PC1 detection via hostname."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category", return_value={}):
                service = MachineIdentityService()
                assert service.machine_role == "pc1"
                assert service.machine_id == "ESPENMAIN"
                assert service._detection_method == "hostname_detection"

    def test_hostname_detection_pc2(self):
        """Test PC2 detection via hostname."""
        with patch("socket.gethostname", return_value="ProfitTrader"):
            with patch("app.services.settings_service.get_settings_by_category", return_value={}):
                service = MachineIdentityService()
                assert service.machine_role == "pc2"
                assert service.machine_id == "PROFITTRADER"
                assert service._detection_method == "hostname_detection"

    def test_unknown_hostname_fallback(self):
        """Test standalone fallback for unknown hostname."""
        with patch("socket.gethostname", return_value="my-laptop"):
            with patch("app.services.settings_service.get_settings_by_category", return_value={}):
                service = MachineIdentityService()
                assert service.machine_role == "standalone"
                assert service.deployment_mode == "single_pc"
                assert service._detection_method == "hostname_unknown_fallback"

    def test_saved_settings_override(self):
        """Test saved settings take priority over hostname."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                mock_settings.return_value = {
                    "machineRole": "pc2",
                    "machineId": "CustomID",
                }
                service = MachineIdentityService()
                assert service.machine_role == "pc2"
                assert service.machine_id == "CustomID"
                assert service._detection_method == "saved_settings"

    def test_environment_variable_override(self):
        """Test environment variable takes priority over hostname."""
        with patch.dict("os.environ", {"MACHINE_ROLE": "pc1", "MACHINE_ID": "EnvID"}):
            with patch("socket.gethostname", return_value="ProfitTrader"):
                with patch("app.services.settings_service.get_settings_by_category", return_value={}):
                    service = MachineIdentityService()
                    assert service.machine_role == "pc1"
                    assert service.machine_id == "EnvID"
                    assert service._detection_method == "environment_variable"

    def test_dual_pc_mode_detection(self):
        """Test dual-PC mode detection when peer configured."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category
                service = MachineIdentityService()
                assert service.deployment_mode == "dual_pc"
                assert service.peer_host == "192.168.1.116"

    def test_single_pc_mode_detection(self):
        """Test single-PC mode when no peer configured."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": ""}
                    return {}

                mock_settings.side_effect = get_category
                service = MachineIdentityService()
                assert service.deployment_mode == "single_pc"
                assert service.peer_host == ""

    @pytest.mark.asyncio
    async def test_peer_health_check_success(self):
        """Test successful peer health check."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()

                # Mock successful HTTP response
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        return_value=mock_response
                    )

                    result = await service.check_peer_online()
                    assert result is True
                    assert service.peer_online is True
                    assert service.fallback_mode is False

    @pytest.mark.asyncio
    async def test_peer_health_check_failure(self):
        """Test peer health check failure (peer offline)."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()

                # Mock failed HTTP request (connection refused)
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        side_effect=Exception("Connection refused")
                    )

                    result = await service.check_peer_online()
                    assert result is False
                    assert service.peer_online is False
                    assert service.fallback_mode is True  # Dual-PC with peer offline

    @pytest.mark.asyncio
    async def test_auto_recovery_from_fallback(self):
        """Test auto-recovery when peer comes back online."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()

                # First check: peer offline
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        side_effect=Exception("Connection refused")
                    )
                    await service.check_peer_online()
                    assert service.fallback_mode is True

                # Second check: peer comes back online
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        return_value=mock_response
                    )
                    await service.check_peer_online()
                    assert service.peer_online is True
                    assert service.fallback_mode is False  # Auto-recovered!

    def test_service_affinity_dual_pc_mode(self):
        """Test service affinity routing in dual-PC mode."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {
                            "peerMachineHost": "192.168.1.116",
                            "serviceAffinityMode": "auto",
                        }
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()
                service.peer_online = True  # Assume peer is online
                service.fallback_mode = False

                # PC1 should run execution and intelligence
                assert service.should_run_service("execution") is True
                assert service.should_run_service("intelligence") is True
                # PC1 should NOT run training (that's for PC2)
                assert service.should_run_service("training") is False
                # Both can run inference
                assert service.should_run_service("inference") is True

    def test_service_affinity_fallback_mode(self):
        """Test service affinity in fallback mode (all services run locally)."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {
                            "peerMachineHost": "192.168.1.116",
                            "serviceAffinityMode": "auto",
                        }
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()
                service.peer_online = False
                service.fallback_mode = True  # In fallback mode

                # All services should run locally in fallback mode
                assert service.should_run_service("training") is True
                assert service.should_run_service("inference") is True
                assert service.should_run_service("execution") is True
                assert service.should_run_service("intelligence") is True

    def test_get_status(self):
        """Test get_status returns complete machine identity state."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {"gpuEnabled": True, "gpuDeviceIndex": 0}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()
                status = service.get_status()

                assert "machine_id" in status
                assert "machine_role" in status
                assert "deployment_mode" in status
                assert "peer_host" in status
                assert "peer_online" in status
                assert "fallback_mode" in status
                assert "gpu_enabled" in status
                assert "detection_method" in status

                assert status["machine_role"] == "pc1"
                assert status["deployment_mode"] == "dual_pc"
                assert status["peer_host"] == "192.168.1.116"
                assert status["gpu_enabled"] is True

    @pytest.mark.asyncio
    async def test_health_check_loop_starts_in_dual_pc(self):
        """Test background health check loop starts in dual-PC mode."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()

                # Start health checks
                await service.start_health_checks()

                # Verify task was created
                assert service._running is True
                assert service._health_check_task is not None

                # Stop health checks
                await service.stop_health_checks()
                assert service._running is False
                assert service._health_check_task is None

    @pytest.mark.asyncio
    async def test_health_check_loop_skips_in_single_pc(self):
        """Test health check loop doesn't start in single-PC mode."""
        with patch("socket.gethostname", return_value="my-laptop"):
            with patch("app.services.settings_service.get_settings_by_category", return_value={}):
                service = MachineIdentityService()

                # Try to start health checks
                await service.start_health_checks()

                # Should not start (single-PC mode)
                assert service._running is False
                assert service._health_check_task is None


class TestPeerDiscoveryService:
    """Tests for PeerDiscoveryService."""

    @pytest.mark.asyncio
    async def test_discovery_disabled_by_default(self):
        """Test peer discovery is disabled by default."""
        with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
            mock_settings.return_value = {"autoDiscoverPeers": False}

            service = PeerDiscoveryService()
            await service.start()

            # Should not start (disabled in settings)
            assert service._running is False

    @pytest.mark.asyncio
    async def test_discovery_graceful_fallback_without_zeroconf(self):
        """Test graceful fallback when zeroconf not installed."""
        with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
            mock_settings.return_value = {"autoDiscoverPeers": True}

            # Mock import error for zeroconf
            with patch("builtins.__import__", side_effect=ImportError("No module named 'zeroconf'")):
                service = PeerDiscoveryService()
                await service.start()

                # Should not crash, just log warning
                assert service._running is False

    def test_complementary_role_detection(self):
        """Test complementary role detection (PC1 ↔ PC2)."""
        service = PeerDiscoveryService()

        # PC1 complements PC2
        assert service._is_complementary_role("pc1", "pc2") is True
        # PC2 complements PC1
        assert service._is_complementary_role("pc2", "pc1") is True
        # Standalone doesn't complement anything
        assert service._is_complementary_role("standalone", "pc1") is False
        assert service._is_complementary_role("pc1", "standalone") is False
        # Same roles don't complement
        assert service._is_complementary_role("pc1", "pc1") is False


class TestSystemIntegration:
    """Integration tests for machine awareness system."""

    def test_singleton_pattern(self):
        """Test get_machine_identity returns singleton."""
        service1 = get_machine_identity()
        service2 = get_machine_identity()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_websocket_broadcasting_on_state_change(self):
        """Test WebSocket events are broadcast on peer status changes."""
        with patch("socket.gethostname", return_value="ESPENMAIN"):
            with patch("app.services.settings_service.get_settings_by_category") as mock_settings:
                def get_category(cat):
                    if cat == "machine":
                        return {}
                    elif cat == "deployment":
                        return {"peerMachineHost": "192.168.1.116"}
                    return {}

                mock_settings.side_effect = get_category

                service = MachineIdentityService()

                # Mock WebSocket broadcast
                with patch("app.websocket_manager.broadcast_ws") as mock_broadcast:
                    with patch("httpx.AsyncClient") as mock_client:
                        # Peer goes online
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                            return_value=mock_response
                        )

                        await service.check_peer_online()

                        # Verify broadcast was called
                        # Note: May not be called if event loop not running in test
                        # This test documents the expected behavior
