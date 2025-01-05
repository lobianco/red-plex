"""Module for creating Plex playlists from local torrent files."""

import click
import yaml
from src.infrastructure.cache.collage_playlist_cache import CollagePlaylistCache
from src.infrastructure.logger.logger import logger

class PlaylistCreator:
    """Handles the creation and updating of Plex playlists from torrent files."""

    def __init__(self, plex_manager, gazelle_api, cache_file=None):
        self.plex_manager = plex_manager
        self.gazelle_api = gazelle_api
        self.playlist_cache = CollagePlaylistCache(cache_file)

    def create_or_update_playlist(self, playlist_name, dry_run=False):
        """Creates or updates a Plex playlist based on torrent files."""
        torrents = self.gazelle_api.get_torrents_info()
        
        if dry_run:
            click.echo(f"\nDry run for playlist: {playlist_name}")
            click.echo(f"Found {len(torrents)} torrent files to process")
            
        existing_playlist = self.plex_manager.get_playlist_by_name(playlist_name)
        if existing_playlist and not dry_run:
            # Ask for confirmation if not in dry run mode
            response = click.confirm(
                f'Playlist "{playlist_name}" already exists. Do you want to update it?',
                default=True
            )
            if not response:
                click.echo('Skipping playlist update.')
                return
        
        matched_rating_keys = set()
        matches_found = []
        no_matches = []
        
        for torrent in torrents:
            info_hash = torrent['info_hash']
            if dry_run:
                click.echo(f"\nProcessing torrent: {torrent['filename']}")
                click.echo(f"Info hash: {info_hash}")
                
            rating_keys = self.plex_manager.get_rating_keys(info_hash)
            
            if rating_keys:
                matched_rating_keys.update(int(key) for key in rating_keys)
                matches_found.append(torrent['filename'])
                if dry_run:
                    click.echo(f"✓ Found matching album(s) for {torrent['filename']}")
            else:
                no_matches.append(torrent['filename'])
                if dry_run:
                    click.echo(f"✗ No matching album found for {torrent['filename']}")

        if not matched_rating_keys:
            message = "No matching albums found for any torrents"
            logger.warning(message)
            click.echo(message)
            return

        if dry_run:
            num_matches = len(matched_rating_keys)
            click.echo(f"\nDry Run Summary:")
            click.echo(f"Playlist: {playlist_name}")
            click.echo(f"Action: {'Update' if existing_playlist else 'Create'} playlist")
            click.echo(f"Total torrents processed: {len(torrents)}")
            click.echo(f"Matches found: {len(matches_found)}")
            click.echo(f"Albums to be added: {num_matches}")
            if no_matches:
                click.echo("\nTorrents with no matches:")
                for filename in no_matches:
                    click.echo(f"- {filename}")
            return

        albums = self.plex_manager.fetch_albums_by_keys(list(matched_rating_keys))
        
        if existing_playlist:
            self.plex_manager.add_items_to_playlist(existing_playlist, albums)
            logger.info('Playlist "%s" updated with %d new albums.', playlist_name, len(albums))
            click.echo(f'Playlist "{playlist_name}" updated with {len(albums)} new albums.')
        else:
            playlist = self.plex_manager.create_playlist(playlist_name, albums)
            logger.info('Playlist "%s" created with %d albums.', playlist_name, len(albums))
            click.echo(f'Playlist "{playlist_name}" created with {len(albums)} albums.')