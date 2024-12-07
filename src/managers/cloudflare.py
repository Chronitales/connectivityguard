import aiohttp
from datetime import datetime, timedelta
from typing import Optional
from ..models.config import CloudflareConfig
from ..utils.logger import get_logger

class CloudflareManager:
    def __init__(self, config: CloudflareConfig):
        self.config = config
        self.logger = get_logger()
        self.last_update_time: Optional[datetime] = None
        self.base_url = f"https://api.cloudflare.com/client/v4/zones/{config.zone_id}/dns_records/{config.record_id}"
        
    async def update_dns(self, target_ip: str) -> bool:
        if self.last_update_time:
            time_since_update = (datetime.now() - self.last_update_time).total_seconds()
            if time_since_update < 300: 
                self.logger.warning(f"DNS update attempted too soon. {300 - time_since_update:.0f}s remaining in cooldown")
                return False
                
        headers = {
            'Authorization': f'Bearer {self.config.api_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'type': 'A',
            'content': target_ip,
            'proxied': False # Meek : Never put this thing to True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(self.base_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        self.last_update_time = datetime.now()
                        self.logger.info(f"Successfully updated DNS to {target_ip}")
                        return True
                    else:
                        error_data = await response.json()
                        self.logger.error(f"Failed to update DNS: {error_data}")
                        return False
        except Exception as e:
            self.logger.error(f"Error updating DNS: {str(e)}")
            return False
            
    async def verify_dns(self, expected_ip: str) -> bool:
        headers = {
            'Authorization': f'Bearer {self.config.api_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        current_ip = data['result']['content']
                        return current_ip == expected_ip
                    else:
                        self.logger.error(f"Failed to verify DNS: {await response.text()}")
                        return False
        except Exception as e:
            self.logger.error(f"Error verifying DNS: {str(e)}")
            return False