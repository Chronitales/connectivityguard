import asyncio
import signal
from typing import Optional
import aiohttp
import json
from datetime import datetime

from models.config import Config
from utils.logger import Logger, get_logger
from utils.uptime import UptimeTracker
from managers.cloudflare import CloudflareManager
from managers.websocket import WebSocketManager

class ConnectivityGuard:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = Config.from_yaml(config_path)
        Logger.initialize(self.config.logging)
        self.logger = get_logger()
        
        self.cloudflare = CloudflareManager(self.config.cloudflare)
        self.uptime_tracker = UptimeTracker()
        self.current_ip = self.config.servers.main_ip
        self.is_failover_active = False
        
        self.ws_manager = WebSocketManager(
            self.config.websocket,
            self._handle_disconnect
        )
        
    async def _handle_disconnect(self) -> None:
        """Handle server disconnection"""
        if self.is_failover_active:
            return
            
        self.logger.warning("Server disconnection detected")
        self.uptime_tracker.record_downtime_start()
        
        # Attempt to fail over
        if await self._attempt_failover():
            self.is_failover_active = True
            self.uptime_tracker.record_failover()
            await self._send_webhook_notification("Failover activated")
        
    async def _attempt_failover(self) -> bool:
        for attempt in range(self.config.failover.retry_attempts):
            self.logger.info(f"Failover attempt {attempt + 1}/{self.config.failover.retry_attempts}")
            
            if await self.cloudflare.update_dns(self.config.servers.fallback_ip):
                self.current_ip = self.config.servers.fallback_ip
                return True
                
            await asyncio.sleep(self.config.failover.retry_delay_seconds)
            
        self.logger.error("All failover attempts failed")
        return False
        
    async def _attempt_recovery(self) -> bool:
        self.logger.info("Attempting recovery to main server")
        
        if await self.cloudflare.update_dns(self.config.servers.main_ip):
            self.current_ip = self.config.servers.main_ip
            self.is_failover_active = False
            self.uptime_tracker.record_downtime_end()
            await self._send_webhook_notification("Recovery completed")
            return True
            
        self.logger.error("Recovery attempt failed")
        return False
        
    async def _send_webhook_notification(self, message: str) -> None:
        stats = self.uptime_tracker.get_statistics()
        
        payload = {
            "content": "",
            "embeds": [{
                "title": "Status Update",
                "description": message,
                "color": 16711680 if self.is_failover_active else 65280,
                "fields": [
                    {
                        "name": "Current Status",
                        "value": "Failover Active" if self.is_failover_active else "Normal Operation",
                        "inline": True
                    },
                    {
                        "name": "Uptime",
                        "value": f"{stats['uptime_percentage']:.2f}%",
                        "inline": True
                    },
                    {
                        "name": "Current IP",
                        "value": self.current_ip,
                        "inline": True
                    }
                ],
                "timestamp": datetime.now().isoformat()
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.notifications.webhook_url,
                    json=payload
                ) as response:
                    if response.status != 204:
                        self.logger.error(f"Failed to send webhook: {await response.text()}")
        except Exception as e:
            self.logger.error(f"Error sending webhook: {str(e)}")
            
    async def start(self) -> None:
        self.logger.info("Starting ConnectivityGuard B)")
        
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            
        if not await self.ws_manager.connect():
            self.logger.error("Failed to establish initial WebSocket connection")
            return
            
        try:
            await self.ws_manager.listen()
        except Exception as e:
            self.logger.error(f"Error in main loop: {str(e)}")
        finally:
            await self.stop()
            
    async def stop(self) -> None:
        self.logger.info("Stopping ConnectivityGuard :'(")
        await self.ws_manager.stop()
        
if __name__ == "__main__":
    failover_system = ConnectivityGuard()
    
    try:
        asyncio.run(failover_system.start())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        get_logger().error(f"Fatal error: {str(e)}")