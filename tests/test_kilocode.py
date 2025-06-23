"""
Tests for the Kilo-Code client manager
"""

import json
import os
import platform
from unittest.mock import Mock, patch
from pathlib import Path

import pytest

from mcpm.clients.managers.kilocode import KiloCodeManager
from mcpm.core.schema import STDIOServerConfig


class TestKiloCodeManager:
    """Test cases for KiloCodeManager"""

    def test_kilocode_manager_initialization(self):
        """Test KiloCodeManager initialization with proper client metadata"""
        manager = KiloCodeManager()
        
        assert manager.client_key == "kilo-code"
        assert manager.display_name == "Kilo-Code"
        assert manager.download_url == "https://marketplace.visualstudio.com/items?itemName=kilocode.Kilo-Code"
        assert hasattr(manager, 'config_path')

    def test_kilocode_config_paths_macos(self):
        """Test macOS-specific config path resolution"""
        with patch('platform.system', return_value='Darwin'):
            manager = KiloCodeManager()
            expected_path = os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json")
            assert manager.config_path == expected_path

    def test_kilocode_config_paths_windows(self):
        """Test Windows-specific config path resolution"""
        with patch('platform.system', return_value='Windows'), \
             patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
            manager = KiloCodeManager()
            expected_path = os.path.join("C:\\Users\\Test\\AppData\\Roaming", "Code", "User", "globalStorage", "kilocode.kilo-code", "settings", "mcp_settings.json")
            assert manager.config_path == expected_path

    def test_kilocode_config_paths_linux(self):
        """Test Linux-specific config path resolution"""
        with patch('platform.system', return_value='Linux'):
            manager = KiloCodeManager()
            expected_path = os.path.expanduser("~/.config/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json")
            assert manager.config_path == expected_path

    def test_kilocode_custom_config_path(self):
        """Test initialization with custom config path"""
        custom_path = "/custom/path/config.json"
        manager = KiloCodeManager(config_path=custom_path)
        assert manager.config_path == custom_path

    def test_get_empty_config(self):
        """Test empty config structure generation"""
        manager = KiloCodeManager()
        empty_config = manager._get_empty_config()
        
        assert isinstance(empty_config, dict)
        assert "mcpServers" in empty_config
        assert empty_config["mcpServers"] == {}

    def test_get_client_info(self):
        """Test client information retrieval"""
        manager = KiloCodeManager()
        info = manager.get_client_info()
        
        assert info["name"] == "Kilo-Code"
        assert info["download_url"] == "https://marketplace.visualstudio.com/items?itemName=kilocode.Kilo-Code"
        assert "config_file" in info
        assert info["config_file"] == manager.config_path

    @patch('os.path.isdir')
    def test_is_client_installed_true(self, mock_isdir):
        """Test client installation detection when installed"""
        mock_isdir.return_value = True
        manager = KiloCodeManager()
        
        assert manager.is_client_installed() is True
        mock_isdir.assert_called_once_with(os.path.dirname(manager.config_path))

    @patch('os.path.isdir')
    def test_is_client_installed_false(self, mock_isdir):
        """Test client installation detection when not installed"""
        mock_isdir.return_value = False
        manager = KiloCodeManager()
        
        assert manager.is_client_installed() is False
        mock_isdir.assert_called_once_with(os.path.dirname(manager.config_path))

    def test_server_management_empty_config(self, tmp_path):
        """Test server management with empty config"""
        config_file = tmp_path / "config.json"
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Test getting servers from non-existent config
        servers = manager.get_servers()
        assert servers == {}
        
        # Test listing servers
        server_list = manager.list_servers()
        assert server_list == []

    def test_add_server_to_config(self, tmp_path):
        """Test adding a server to Kilo-Code config"""
        config_file = tmp_path / "config.json"
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Create a test server config
        server_config = STDIOServerConfig(
            name="test-server",
            command="python",
            args=["-m", "test_server"]
        )
        
        # Add the server
        success = manager.add_server(server_config)
        assert success is True
        
        # Verify the server was added
        assert config_file.exists()
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
        assert config["mcpServers"]["test-server"]["command"] == "python"
        assert config["mcpServers"]["test-server"]["args"] == ["-m", "test_server"]

    def test_get_server_from_config(self, tmp_path):
        """Test retrieving a server from Kilo-Code config"""
        config_file = tmp_path / "config.json"
        
        # Create config with a server
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "python",
                    "args": ["-m", "test_server"]
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Get the server
        server_config = manager.get_server("test-server")
        assert server_config is not None
        assert server_config.name == "test-server"
        assert server_config.command == "python"
        assert server_config.args == ["-m", "test_server"]
        
        # Test non-existent server
        non_existent = manager.get_server("non-existent")
        assert non_existent is None

    def test_remove_server_from_config(self, tmp_path):
        """Test removing a server from Kilo-Code config"""
        config_file = tmp_path / "config.json"
        
        # Create config with servers
        config_data = {
            "mcpServers": {
                "test-server-1": {
                    "command": "python",
                    "args": ["-m", "test_server_1"]
                },
                "test-server-2": {
                    "command": "node",
                    "args": ["test_server_2.js"]
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Remove one server
        success = manager.remove_server("test-server-1")
        assert success is True
        
        # Verify removal
        servers = manager.get_servers()
        assert "test-server-1" not in servers
        assert "test-server-2" in servers
        
        # Test removing non-existent server
        success = manager.remove_server("non-existent")
        assert success is False

    def test_disable_enable_server(self, tmp_path):
        """Test server disable/enable functionality"""
        config_file = tmp_path / "config.json"
        
        # Create config with a server
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "python",
                    "args": ["-m", "test_server"]
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Test server is initially not disabled
        assert manager.is_server_disabled("test-server") is False
        
        # Disable the server
        success = manager.disable_server("test-server")
        assert success is True
        assert manager.is_server_disabled("test-server") is True
        
        # Re-enable the server
        success = manager.enable_server("test-server")
        assert success is True
        assert manager.is_server_disabled("test-server") is False
        
        # Test disabling non-existent server
        success = manager.disable_server("non-existent")
        assert success is False
        
        # Test enabling non-existent server
        success = manager.enable_server("non-existent")
        assert success is False

    def test_corrupt_config_handling(self, tmp_path):
        """Test handling of corrupt JSON config files"""
        config_file = tmp_path / "config.json"
        
        # Create a corrupt JSON file
        with open(config_file, 'w') as f:
            f.write("{ invalid json content }")
        
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Should handle corrupt config gracefully
        servers = manager.get_servers()
        assert servers == {}
        
        # Should be able to add servers (will create new valid config)
        server_config = STDIOServerConfig(
            name="test-server",
            command="python",
            args=["-m", "test_server"]
        )
        
        success = manager.add_server(server_config)
        assert success is True

    def test_config_directory_creation(self, tmp_path):
        """Test that config directory is created when adding servers"""
        config_dir = tmp_path / "nested" / "directory" / "structure"
        config_file = config_dir / "config.json"
        
        manager = KiloCodeManager(config_path=str(config_file))
        
        # Directory shouldn't exist initially
        assert not config_dir.exists()
        
        # Add a server (should create directory structure)
        server_config = STDIOServerConfig(
            name="test-server",
            command="python",
            args=["-m", "test_server"]
        )
        
        success = manager.add_server(server_config)
        assert success is True
        
        # Directory and file should now exist
        assert config_dir.exists()
        assert config_file.exists()


class TestKiloCodeManagerIntegration:
    """Integration tests for KiloCodeManager with the client registry"""

    def test_manager_registration(self):
        """Test that KiloCodeManager is properly registered"""
        from mcpm.clients.client_registry import ClientRegistry
        
        # Test manager can be retrieved
        manager = ClientRegistry.get_client_manager("kilo-code")
        assert manager is not None
        assert isinstance(manager, KiloCodeManager)
        
        # Test manager appears in supported clients
        supported_clients = ClientRegistry.get_supported_clients()
        assert "kilo-code" in supported_clients
        
        # Test client info is available
        client_info = ClientRegistry.get_client_info("kilo-code")
        assert client_info["name"] == "Kilo-Code"
        assert "kilocode.Kilo-Code" in client_info["download_url"]

    def test_manager_in_all_clients(self):
        """Test that KiloCodeManager appears in all client operations"""
        from mcpm.clients.client_registry import ClientRegistry
        
        all_managers = ClientRegistry.get_all_client_managers()
        assert "kilo-code" in all_managers
        assert isinstance(all_managers["kilo-code"], KiloCodeManager)
        
        all_info = ClientRegistry.get_all_client_info()
        assert "kilo-code" in all_info
        assert all_info["kilo-code"]["name"] == "Kilo-Code"

    def test_installation_detection_integration(self):
        """Test installation detection through registry"""
        from mcpm.clients.client_registry import ClientRegistry
        
        with patch.object(KiloCodeManager, 'is_client_installed', return_value=True):
            installed_clients = ClientRegistry.detect_installed_clients()
            assert "kilo-code" in installed_clients
            assert installed_clients["kilo-code"] is True
        
        with patch.object(KiloCodeManager, 'is_client_installed', return_value=False):
            installed_clients = ClientRegistry.detect_installed_clients()
            assert "kilo-code" in installed_clients
            assert installed_clients["kilo-code"] is False