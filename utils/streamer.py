"""
ByteStreamer - Core streaming functionality.

This module handles the actual streaming of files from Telegram servers
to HTTP clients without saving to disk.
"""

import asyncio
import logging
import math
from typing import AsyncGenerator, Dict, Optional, Tuple, Union

from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.file_id import FileId, FileType
from pyrogram.raw.functions.upload import GetFile
from pyrogram.raw.types import (
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    InputPeerPhotoFileLocation,
)
from pyrogram.types import Message

import config

logger = logging.getLogger(__name__)


class FileNotFoundError(Exception):
    """Raised when a file is not found."""
    pass


class StreamerError(Exception):
    """Base exception for streamer errors."""
    pass


class ByteStreamer:
    """
    Handles streaming of Telegram files to HTTP clients.
    
    This class provides methods to:
    - Get file properties from messages
    - Stream file chunks from Telegram servers
    - Handle range requests for seeking
    """
    
    def __init__(self, client: Client):
        """
        Initialize the ByteStreamer.
        
        Args:
            client: The Pyrogram client instance
        """
        self.client = client
        self._cache: Dict[int, dict] = {}  # Cache for file properties
    
    async def get_message(self, message_id: int) -> Message:
        """
        Get a message from the log channel by ID.
        
        Args:
            message_id: The message ID to fetch
            
        Returns:
            The message object
            
        Raises:
            FileNotFoundError: If message is not found
        """
        try:
            message = await self.client.get_messages(
                chat_id=config.LOG_CHANNEL,
                message_ids=message_id
            )
            
            if not message or message.empty:
                raise FileNotFoundError(f"Message {message_id} not found")
            
            return message
            
        except Exception as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            raise FileNotFoundError(f"Could not fetch message: {e}")
    
    def get_media_from_message(self, message: Message) -> Optional[object]:
        """
        Extract media object from a message.
        
        Args:
            message: The message to extract media from
            
        Returns:
            The media object or None
        """
        if message.video:
            return message.video
        elif message.document:
            return message.document
        elif message.audio:
            return message.audio
        elif message.voice:
            return message.voice
        elif message.video_note:
            return message.video_note
        elif message.animation:
            return message.animation
        elif message.photo:
            return message.photo[-1]  # Highest resolution
        return None
    
    async def get_file_properties(self, message_id: int) -> dict:
        """
        Get file properties for a message ID.
        
        Args:
            message_id: The message ID in the log channel
            
        Returns:
            Dictionary with file properties
        """
        # Check cache first
        if message_id in self._cache:
            return self._cache[message_id]
        
        # Fetch message
        message = await self.get_message(message_id)
        media = self.get_media_from_message(message)
        
        if not media:
            raise FileNotFoundError("No media found in message")
        
        properties = {
            "file_id": media.file_id,
            "file_unique_id": media.file_unique_id,
            "file_size": getattr(media, "file_size", 0),
            "file_name": getattr(media, "file_name", "file"),
            "mime_type": getattr(media, "mime_type", "application/octet-stream"),
        }
        
        # Cache the properties
        self._cache[message_id] = properties
        
        return properties
    
    def parse_range_header(
        self, 
        range_header: str, 
        file_size: int
    ) -> Tuple[int, int]:
        """
        Parse HTTP Range header.
        
        Args:
            range_header: The Range header value
            file_size: Total file size
            
        Returns:
            Tuple of (start, end) byte positions
        """
        if not range_header or not range_header.startswith("bytes="):
            return 0, file_size - 1
        
        range_str = range_header[6:]  # Remove "bytes="
        
        if range_str.startswith("-"):
            # Suffix range: last N bytes
            suffix_length = int(range_str[1:])
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif range_str.endswith("-"):
            # Range from start to end
            start = int(range_str[:-1])
            end = file_size - 1
        else:
            # Explicit range
            parts = range_str.split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else file_size - 1
        
        # Validate range
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))
        
        return start, end
    
    def get_file_location(self, file_id_str: str):
        """
        Create file location for Telegram API.
        
        Args:
            file_id_str: The file_id string
            
        Returns:
            InputFileLocation object for the Telegram API
        """
        file_id = FileId.decode(file_id_str)
        
        file_type = file_id.file_type
        
        if file_type in (
            FileType.DOCUMENT,
            FileType.VIDEO,
            FileType.AUDIO,
            FileType.VOICE,
            FileType.VIDEO_NOTE,
            FileType.ANIMATION,
            FileType.STICKER,
        ):
            return InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=""
            )
        elif file_type == FileType.PHOTO:
            return InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size="y"
            )
        else:
            raise StreamerError(f"Unsupported file type: {file_type}")
    
    async def yield_file(
        self,
        file_id: str,
        offset: int = 0,
        limit: int = 0,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream file chunks from Telegram.
        
        Args:
            file_id: The Telegram file_id
            offset: Starting byte position
            limit: Maximum bytes to stream (0 = until end)
            
        Yields:
            File chunks as bytes
        """
        file_location = self.get_file_location(file_id)
        
        current_offset = offset
        chunk_size = config.CHUNK_SIZE
        
        # Calculate end position
        if limit > 0:
            end_offset = offset + limit
        else:
            end_offset = float('inf')  # Will stop when server returns empty
        
        while current_offset < end_offset:
            try:
                # Request chunk from Telegram
                result = await self.client.invoke(
                    GetFile(
                        location=file_location,
                        offset=current_offset,
                        limit=chunk_size
                    ),
                    sleep_threshold=30
                )
                
                if not result.bytes:
                    # No more data
                    break
                
                chunk = bytes(result.bytes)
                
                # If limit is set, only yield up to the limit
                if limit > 0:
                    remaining = end_offset - current_offset
                    if len(chunk) > remaining:
                        chunk = chunk[:remaining]
                
                yield chunk
                
                current_offset += len(chunk)
                
                # If we got less than requested, we've reached the end
                if len(result.bytes) < chunk_size:
                    break
                    
            except FloodWait as e:
                logger.warning(f"FloodWait: sleeping for {e.value} seconds")
                await asyncio.sleep(e.value)
                continue
            except Exception as e:
                logger.error(f"Error streaming chunk at offset {current_offset}: {e}")
                raise StreamerError(f"Streaming error: {e}")
    
    def clear_cache(self, message_id: Optional[int] = None):
        """
        Clear the file properties cache.
        
        Args:
            message_id: Specific message to clear, or None to clear all
        """
        if message_id:
            self._cache.pop(message_id, None)
        else:
            self._cache.clear()
