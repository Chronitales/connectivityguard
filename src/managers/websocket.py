import asyncio
import websockets
from websockets.exceptions import WebSocketException
from datetime import datetime
from typing import Optional, Callable, Awaitable
from ..models.config import WebsocketConfig
from ..utils.logger import get_logger

class WebSocketManager:
    def __init__(self, config: WebsocketConfig, 
                 on_disconnect: Callable[[], Awaitable[None]]):
        self.config = config
        self.logger = get_logger()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.last_heartbeat: Optional[datetime] = None
        self.on_disconnect = on_disconnect
        self.reconnect_attempts = 0
        self.running = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        while self.reconnect_attempts < self.config.max_reconnect_attempts:
            try:
                self.ws = await websockets.connect(self.config.websocket_url)
                self.logger.info("Successfully connected")
                self.reconnect_attempts = 0
                self.running = True
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                return True
            except Exception as e:
                self.reconnect_attempts += 1
                delay = self.config.base_reconnect_delay * (2 ** self.reconnect_attempts)
                self.logger.warning(
                    f"Connection attempt {self.reconnect_attempts} failed: {str(e)}. "
                    f"Retrying in {delay} seconds..."
                )
                await asyncio.sleep(delay)
        
        self.logger.error("Max reconnection attempts reached")
        await self.on_disconnect()
        return False
        
    async def _heartbeat_loop(self) -> None:
        while self.running:
            try:
                if self.ws and not self.ws.closed:
                    await self.ws.send('{"type": "heartbeat"}')
                    self.last_heartbeat = datetime.now()
                    self.logger.debug("Heartbeat sent")
                await asyncio.sleep(self.config.heartbeat_interval)
            except WebSocketException as e:
                self.logger.error(f"WebSocket error during heartbeat: {str(e)}")
                await self.on_disconnect()
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {str(e)}")
                await asyncio.sleep(self.config.heartbeat_interval)
                
    async def listen(self) -> None:
        while self.running:
            try:
                if not self.ws or self.ws.closed:
                    self.logger.warning("WebSocket connection lost, attempting to reconnect...")
                    if not await self.connect():
                        break
                    
                message = await self.ws.recv()
                await self._handle_message(message)
                
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
                await self.on_disconnect()
                if not await self.connect():
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in message loop: {str(e)}")
                await asyncio.sleep(1)
                
    async def _handle_message(self, message: str) -> None:
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'status':
                await self._handle_status_message(data)
            elif message_type == 'error':
                await self._handle_error_message(data)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            self.logger.error("Failed to parse WebSocket message as JSON")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            
    async def _handle_status_message(self, data: dict) -> None:
        try:
            server_status = data.get('status')
            players_online = data.get('players', 0)
            tps = data.get('tps', 0)
            
            self.logger.info(
                f"Server status update - Status: {server_status}, "
                f"Players: {players_online}, TPS: {tps}"
            )
            if server_status != 'healthy':
                await self.on_disconnect()
                
        except Exception as e:
            self.logger.error(f"Error handling status message: {str(e)}")
            
    async def _handle_error_message(self, data: dict) -> None:
        error_type = data.get('error_type')
        error_message = data.get('message')
        self.logger.error(f"Server error - Type: {error_type}, Message: {error_message}")
        
    async def stop(self) -> None:
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
                
        if self.ws:
            await self.ws.close()
            self.ws = None
            
    async def send_message(self, message: dict) -> bool:
        if not self.ws or self.ws.closed:
            self.logger.error("Cannot send message - WebSocket is not connected")
            return False
            
        try:
            await self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False