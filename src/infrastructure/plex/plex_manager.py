"""Module for managing Plex albums and playlists."""

import os
import yaml
from datetime import datetime, timezone
from plexapi.server import PlexServer
from src.infrastructure.logger.logger import logger
from src.infrastructure.cache.album_cache import AlbumCache

class PlexManager:
    """Handles operations related to Plex."""

    def __init__(self, url, token, section_name, csv_file=None):
        self.url = url
        self.token = token
        self.section_name = section_name
        self.plex = PlexServer(self.url, self.token)
        self.library_section = self.plex.library.section(self.section_name)

        # Initialize the album cache
        self.album_cache = AlbumCache(csv_file)
        self.album_data = self.album_cache.load_albums()

    def read_origin_yaml(self, album_path):
        """Read origin.yaml file from an album directory."""
        origin_file = os.path.join(album_path, 'origin.yaml')
        try:
            with open(origin_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.debug('Failed to read origin.yaml in %s: %s', album_path, e)
            return None

    def populate_album_cache(self):
        """Fetches new albums from Plex and updates the cache."""
        logger.info('Updating album cache...')

        # Determine the latest addedAt date from the existing cache
        if self.album_data:
            latest_added_at = max(added_at for _, (_, added_at, _) in self.album_data.items())
            logger.info('Latest album added at: %s', latest_added_at)
        else:
            latest_added_at = datetime(1970, 1, 1, tzinfo=timezone.utc)
            logger.info('No existing albums in cache. Fetching all albums.')

        # Fetch albums added after the latest date in cache
        filters = {"addedAt>>": latest_added_at}
        new_albums = self.library_section.searchAlbums(filters=filters)
        logger.info('Found %d new albums added after %s.', len(new_albums), latest_added_at)

        # Update the album_data dictionary with new albums
        for album in new_albums:
            tracks = album.tracks()
            if tracks:
                media_path = tracks[0].media[0].parts[0].file
                album_folder_path = os.path.dirname(media_path)
                added_at = album.addedAt

                # Read info hash from origin.yaml
                origin_data = self.read_origin_yaml(album_folder_path)
                info_hash = origin_data.get('Info hash') if origin_data else None
                
                if info_hash:
                    logger.debug('Found info hash %s for album %s', info_hash, album_folder_path)
                else:
                    logger.debug('No info hash found for album %s', album_folder_path)

                self.album_data[int(album.ratingKey)] = (album_folder_path, added_at, info_hash)
            else:
                logger.warning('Skipping album with no tracks: %s', album.title)

        # Save the updated album data to the cache
        self.album_cache.save_albums(self.album_data)

    def reset_album_cache(self):
        """Resets the album cache by deleting the cache file."""
        self.album_cache.reset_cache()
        self.album_data = {}
        logger.info('Album cache has been reset.')

    def get_rating_keys(self, info_hash):
        """Returns the rating keys if the info hash matches an album's cache entry."""
        rating_keys = [
            key for key, (_, _, album_hash) in self.album_data.items() 
            if album_hash and album_hash.upper() == info_hash.upper()
        ]
        
        if rating_keys:
            logger.info('Matched album by info hash %s', info_hash)
            return rating_keys
        
        logger.debug('No matches found for info hash %s', info_hash)
        return []

    def fetch_albums_by_keys(self, rating_keys):
        """Fetches album objects from Plex using their rating keys."""
        logger.info('Fetching albums from Plex using rating keys: %s', rating_keys)
        return self.plex.fetchItems(rating_keys)

    def create_playlist(self, name, albums):
        """Creates a playlist in Plex."""
        logger.info('Creating playlist with name "%s" and %d albums.', name, len(albums))
        playlist = self.plex.createPlaylist(name, self.section_name, albums)
        return playlist

    def create_collection(self, name, albums):
        """Creates a collection in Plex."""
        logger.info('Creating collection with name "%s" and %d albums.', name, len(albums))
        collection = self.library_section.createCollection(name, items=albums)
        return collection

    def get_playlist_by_name(self, name):
        """Finds a playlist by name."""
        playlists = self.plex.playlists()
        for playlist in playlists:
            if playlist.title == name:
                logger.info('Found existing playlist with name "%s".', name)
                return playlist
        logger.info('No existing playlist found with name "%s".', name)
        return None

    def get_collection_by_name(self, name):
        """Finds a collection by name."""
        collections = self.library_section.collections()
        for collection in collections:
            if collection.title == name:
                logger.info('Found existing collection with name "%s".', name)
                return collection
        logger.info('No existing collection found with name "%s".', name)
        return None

    def add_items_to_playlist(self, playlist, albums):
        """Adds albums to an existing playlist."""
        logger.info('Adding %d albums to playlist "%s".', len(albums), playlist.title)
        playlist.addItems(albums)

    def add_items_to_collection(self, collection, albums):
        """Adds albums to an existing collection."""
        logger.info('Adding %d albums to collection "%s".', len(albums), collection.title)
        collection.addItems(albums)