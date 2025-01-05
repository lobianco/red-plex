"""Module for creating Plex collections from local torrent files."""

import logging
import click
from src.infrastructure.logger.logger import logger

class CollectionCreator:
    """Handles the creation and updating of Plex collections from local torrent files."""

    def __init__(self, plex_manager, gazelle_api):
        self.plex_manager = plex_manager
        self.gazelle_api = gazelle_api

    def create_or_update_collection(self, collection_name, dry_run=False):
        """Creates or updates a Plex collection based on local torrent files."""
        torrents = self.gazelle_api.get_torrents_info()
        
        if dry_run:
            click.echo(f"\nDry run for collection: {collection_name}")
            click.echo(f"Found {len(torrents)} torrent files to process")
            
        existing_collection = self.plex_manager.get_collection_by_name(collection_name)
        if existing_collection and not dry_run:
            response = click.confirm(
                f'Collection "{collection_name}" already exists. Do you want to update it?',
                default=True
            )
            if not response:
                click.echo('Skipping collection update.')
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
            click.echo(f"Collection: {collection_name}")
            click.echo(f"Action: {'Update' if existing_collection else 'Create'} collection")
            click.echo(f"Total torrents processed: {len(torrents)}")
            click.echo(f"Matches found: {len(matches_found)}")
            click.echo(f"Albums to be added: {num_matches}")
            if no_matches:
                click.echo("\nTorrents with no matches:")
                for filename in no_matches:
                    click.echo(f"- {filename}")
            return

        albums = self.plex_manager.fetch_albums_by_keys(list(matched_rating_keys))
        
        if existing_collection:
            self.plex_manager.add_items_to_collection(existing_collection, albums)
            logger.info('Collection "%s" updated with %d new albums.', collection_name, len(albums))
            click.echo(f'Collection "{collection_name}" updated with {len(albums)} new albums.')
        else:
            collection = self.plex_manager.create_collection(collection_name, albums)
            logger.info('Collection "%s" created with %d albums.', collection_name, len(albums))
            click.echo(f'Collection "{collection_name}" created with {len(albums)} albums.')