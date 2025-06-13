"""
User-specific Notification System
Handles notifications for individual users
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
import aiohttp
import redis.asyncio as redis
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Notification:
    """Notification data structure"""
    user_id: str
    type: str
    title: str
    message: str
    priority: str
    timestamp: datetime
    read: bool
    data: Dict

class NotificationManager:
    """Manages user-specific notifications"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis = redis.from_url(config['redis_url'])
        self.slack_webhook = config.get('slack_webhook_url')
        self.email_config = config.get('email')
        
    async def send_notification(self, user_id: str, notification: Notification) -> bool:
        """Send a notification to a user"""
        try:
            # Store notification
            await self._store_notification(user_id, notification)
            
            # Get user preferences
            preferences = await self._get_user_preferences(user_id)
            
            # Send through configured channels
            if preferences.get('notifications', {}).get('slack', False):
                await self._send_slack_notification(user_id, notification)
                
            if preferences.get('notifications', {}).get('email', False):
                await self._send_email_notification(user_id, notification)
                
            if preferences.get('notifications', {}).get('in_app', True):
                await self._send_in_app_notification(user_id, notification)
                
            logger.info(f"Notification sent to user {user_id}: {notification.type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
            return False
            
    async def get_user_notifications(self, user_id: str, unread_only: bool = False,
                                   limit: int = 50) -> List[Notification]:
        """Get user's notifications"""
        try:
            # Get notifications from Redis
            notifications = []
            async for key in self.redis.scan_iter(f"user:{user_id}:notifications:*"):
                notification_data = await self.redis.hgetall(key)
                if notification_data:
                    notification = Notification(
                        user_id=user_id,
                        type=notification_data['type'],
                        title=notification_data['title'],
                        message=notification_data['message'],
                        priority=notification_data['priority'],
                        timestamp=datetime.fromisoformat(notification_data['timestamp']),
                        read=notification_data['read'] == 'True',
                        data=json.loads(notification_data['data'])
                    )
                    
                    if not unread_only or not notification.read:
                        notifications.append(notification)
                        
            # Sort by timestamp and limit
            notifications.sort(key=lambda x: x.timestamp, reverse=True)
            return notifications[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            return []
            
    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        try:
            await self.redis.hset(
                f"user:{user_id}:notifications:{notification_id}",
                'read',
                'True'
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read for user {user_id}: {e}")
            return False
            
    async def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """Delete a notification"""
        try:
            await self.redis.delete(f"user:{user_id}:notifications:{notification_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete notification for user {user_id}: {e}")
            return False
            
    async def _store_notification(self, user_id: str, notification: Notification):
        """Store notification in Redis"""
        try:
            notification_id = f"{datetime.now().timestamp()}"
            await self.redis.hset(
                f"user:{user_id}:notifications:{notification_id}",
                mapping={
                    'type': notification.type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'timestamp': notification.timestamp.isoformat(),
                    'read': str(notification.read),
                    'data': json.dumps(notification.data)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store notification for user {user_id}: {e}")
            
    async def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user's notification preferences"""
        try:
            preferences = await self.redis.hgetall(f"user:{user_id}:preferences")
            return json.loads(preferences.get('notifications', '{}'))
            
        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}")
            return {}
            
    async def _send_slack_notification(self, user_id: str, notification: Notification):
        """Send notification via Slack"""
        try:
            if not self.slack_webhook:
                return
                
            # Get user's Slack channel
            user_data = await self.redis.hgetall(f"user:{user_id}")
            slack_channel = user_data.get('slack_channel')
            
            if not slack_channel:
                return
                
            # Prepare message
            message = {
                "channel": slack_channel,
                "text": f"*{notification.title}*\n{notification.message}",
                "attachments": [{
                    "color": self._get_priority_color(notification.priority),
                    "fields": [
                        {
                            "title": "Type",
                            "value": notification.type,
                            "short": True
                        },
                        {
                            "title": "Priority",
                            "value": notification.priority,
                            "short": True
                        }
                    ],
                    "ts": notification.timestamp.timestamp()
                }]
            }
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook, json=message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification for user {user_id}: {e}")
            
    async def _send_email_notification(self, user_id: str, notification: Notification):
        """Send notification via email"""
        try:
            if not self.email_config:
                return
                
            # Get user's email
            user_data = await self.redis.hgetall(f"user:{user_id}")
            email = user_data.get('email')
            
            if not email:
                return
                
            # Prepare email
            subject = f"[{notification.priority}] {notification.title}"
            body = f"""
            {notification.message}
            
            Type: {notification.type}
            Priority: {notification.priority}
            Time: {notification.timestamp}
            """
            
            # Send email
            # In production, use proper email sending library
            logger.info(f"Would send email to {email}: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification for user {user_id}: {e}")
            
    async def _send_in_app_notification(self, user_id: str, notification: Notification):
        """Send in-app notification"""
        try:
            # Store in Redis for real-time delivery
            await self.redis.publish(
                f"user:{user_id}:notifications",
                json.dumps({
                    'type': notification.type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'timestamp': notification.timestamp.isoformat(),
                    'data': notification.data
                })
            )
            
        except Exception as e:
            logger.error(f"Failed to send in-app notification for user {user_id}: {e}")
            
    def _get_priority_color(self, priority: str) -> str:
        """Get color for priority level"""
        colors = {
            'high': '#FF0000',  # Red
            'medium': '#FFA500',  # Orange
            'low': '#00FF00'  # Green
        }
        return colors.get(priority.lower(), '#808080')  # Default to gray 