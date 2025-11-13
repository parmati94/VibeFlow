import { getSpotifyPlaylist, getSpotifyPlaylistTracks } from './spotifyService.js';
import { 
  createTidalPlaylist, 
  searchTidalByISRC, 
  searchTidalByMetadata,
  addTracksToTidalPlaylist 
} from './tidalService.js';

/**
 * Sync a Spotify playlist to Tidal
 * Strategy: Use ISRC codes as primary matching method, fall back to metadata search
 */
export async function syncPlaylist({ spotifyPlaylistId, tidalPlaylistName, spotifyToken, tidalToken }) {
  const stats = {
    totalTracks: 0,
    matchedByISRC: 0,
    matchedByMetadata: 0,
    notFound: 0,
    addedToTidal: 0
  };

  try {
    // 1. Get Spotify playlist details and tracks
    console.log('Fetching Spotify playlist...');
    const spotifyPlaylist = await getSpotifyPlaylist(spotifyPlaylistId, spotifyToken);
    const spotifyTracks = await getSpotifyPlaylistTracks(spotifyPlaylistId, spotifyToken);
    
    stats.totalTracks = spotifyTracks.length;
    console.log(`Found ${stats.totalTracks} tracks in "${spotifyPlaylist.name}"`);

    if (spotifyTracks.length === 0) {
      return {
        success: true,
        message: 'Playlist is empty',
        stats
      };
    }

    // 2. Create Tidal playlist
    console.log('Creating Tidal playlist...');
    const playlistName = tidalPlaylistName || spotifyPlaylist.name;
    const tidalPlaylistId = await createTidalPlaylist(
      playlistName,
      spotifyPlaylist.description || `Synced from Spotify playlist "${spotifyPlaylist.name}"`,
      tidalToken
    );
    console.log(`Created Tidal playlist: ${playlistName}`);

    // 3. Match tracks
    console.log('Matching tracks...');
    const matchedTracks = [];
    const unmatchedTracks = [];

    for (let i = 0; i < spotifyTracks.length; i++) {
      const track = spotifyTracks[i];
      console.log(`[${i + 1}/${spotifyTracks.length}] Matching: ${track.name} - ${track.artists.join(', ')}`);
      
      let tidalTrackId = null;

      // Try ISRC first (most accurate)
      if (track.isrc) {
        tidalTrackId = await searchTidalByISRC(track.isrc, tidalToken);
        if (tidalTrackId) {
          stats.matchedByISRC++;
          console.log(`  ✓ Matched by ISRC`);
        }
      }

      // Fall back to metadata search
      if (!tidalTrackId) {
        tidalTrackId = await searchTidalByMetadata(track.name, track.artists, tidalToken);
        if (tidalTrackId) {
          stats.matchedByMetadata++;
          console.log(`  ✓ Matched by metadata`);
        } else {
          console.log(`  ✗ Not found`);
        }
      }

      if (tidalTrackId) {
        matchedTracks.push({
          ...track,
          tidalId: tidalTrackId
        });
      } else {
        unmatchedTracks.push(track);
        stats.notFound++;
      }

      // Small delay to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // 4. Add matched tracks to Tidal playlist
    if (matchedTracks.length > 0) {
      console.log(`Adding ${matchedTracks.length} tracks to Tidal playlist...`);
      const tidalTrackIds = matchedTracks.map(t => t.tidalId);
      await addTracksToTidalPlaylist(tidalPlaylistId, tidalTrackIds, tidalToken);
      stats.addedToTidal = matchedTracks.length;
      console.log('✓ Tracks added successfully');
    }

    // 5. Return results
    return {
      success: true,
      message: `Successfully synced ${matchedTracks.length} of ${stats.totalTracks} tracks`,
      stats,
      tidalPlaylistId,
      unmatchedTracks: unmatchedTracks.map(t => ({
        name: t.name,
        artists: t.artists
      }))
    };

  } catch (error) {
    console.error('Sync error:', error);
    throw new Error(error.message || 'Failed to sync playlist');
  }
}
