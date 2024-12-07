from datetime import datetime, timedelta
from typing import List, Tuple, Optional

class UptimeTracker:
    def __init__(self):
        self.start_time = datetime.now()
        self.downtime_periods: List[Tuple[datetime, datetime]] = []
        self.current_downtime_start: Optional[datetime] = None
        self.failover_count = 0
        
    def record_downtime_start(self) -> None:
        if self.current_downtime_start is None:
            self.current_downtime_start = datetime.now()
            
    def record_downtime_end(self) -> None:
        if self.current_downtime_start is not None:
            downtime_period = (self.current_downtime_start, datetime.now())
            self.downtime_periods.append(downtime_period)
            self.current_downtime_start = None
            
    def record_failover(self) -> None:
        self.failover_count += 1
            
    def get_uptime_percentage(self) -> float:
        total_downtime = timedelta()
        for start, end in self.downtime_periods:
            total_downtime += end - start
            
        if self.current_downtime_start:
            total_downtime += datetime.now() - self.current_downtime_start
            
        total_time = datetime.now() - self.start_time
        uptime = total_time - total_downtime
        return (uptime.total_seconds() / total_time.total_seconds()) * 100
        
    def get_statistics(self) -> dict:
        return {
            'uptime_percentage': self.get_uptime_percentage(),
            'total_downtime': sum((end - start).total_seconds() 
                                for start, end in self.downtime_periods),
            'failover_count': self.failover_count,
            'start_time': self.start_time.isoformat(),
            'current_status': 'down' if self.current_downtime_start else 'up',
            'total_incidents': len(self.downtime_periods)
        }