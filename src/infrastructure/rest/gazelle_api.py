"""Module for scanning local torrent files."""

import os
import hashlib
import bencodepy
from src.infrastructure.logger.logger import logger

class GazelleAPI:
    """Handles scanning of local torrent files."""
    
    def __init__(self, torrent_dir):
        """Initialize with directory containing torrent files."""
        self.torrent_dir = torrent_dir

    def get_info_hash(self, torrent_path):
        """Extract info hash from a torrent file."""
        try:
            with open(torrent_path, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
                
            # Get the info dictionary and encode it
            info = torrent_data[b'info']
            info_encoded = bencodepy.encode(info)
            
            # Calculate SHA1 hash
            return hashlib.sha1(info_encoded).hexdigest().upper()
        except Exception as e:
            logger.warning('Failed to extract info hash from %s: %s', torrent_path, e)
            return None

    def get_torrents_info(self):
        """Scan directory for torrent files and extract their info hashes."""
        torrents = []
        for filename in os.listdir(self.torrent_dir):
            if not filename.endswith('.torrent'):
                continue
                
            torrent_path = os.path.join(self.torrent_dir, filename)
            info_hash = self.get_info_hash(torrent_path)
            
            if info_hash:
                torrents.append({
                    'info_hash': info_hash,
                    'path': torrent_path,
                    'filename': filename
                })
                logger.debug('Found torrent %s with info hash %s', filename, info_hash)
            
        return torrents