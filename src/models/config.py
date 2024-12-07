from dataclasses import dataclass
import yaml
from typing import Dict, Any

@dataclass
class CloudflareConfig:
    api_token: str
    zone_id: str
    record_id: str

@dataclass
class ServersConfig:
    main_ip: str
    fallback_ip: str
    websocket_url: str

@dataclass
class FailoverConfig:
    cooldown_seconds: int
    retry_attempts: int
    retry_delay_seconds: int

@dataclass
class WebsocketConfig:
    max_reconnect_attempts: int
    base_reconnect_delay: int
    heartbeat_interval: int

@dataclass
class NotificationsConfig:
    webhook_url: str

@dataclass
class LoggingConfig:
    file_path: str
    max_size_mb: int
    backup_count: int
    level: str

@dataclass
class Config:
    cloudflare: CloudflareConfig
    servers: ServersConfig
    failover: FailoverConfig
    websocket: WebsocketConfig
    notifications: NotificationsConfig
    logging: LoggingConfig

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
            
        return cls(
            cloudflare=CloudflareConfig(**config_dict['cloudflare']),
            servers=ServersConfig(**config_dict['servers']),
            failover=FailoverConfig(**config_dict['failover']),
            websocket=WebsocketConfig(**config_dict['websocket']),
            notifications=NotificationsConfig(**config_dict['notifications']),
            logging=LoggingConfig(**config_dict['logging'])
        )

    def validate(self) -> None:
        """Validate configuration values"""
        if self.failover.cooldown_seconds < 0:
            raise ValueError("Cooldown seconds must be positive")
        if self.failover.retry_attempts < 1:
            raise ValueError("Retry attempts must be at least 1")
        if not self.cloudflare.api_token:
            raise ValueError("Cloudflare API token is required")