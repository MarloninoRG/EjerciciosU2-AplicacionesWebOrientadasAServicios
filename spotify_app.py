from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'Marloneselmejordesarrollador1'  # Cambiar por una clave secreta

# Spotify API Credentials
CLIENT_ID = '2ef336b8fff54edc8192292059f6616a'
CLIENT_SECRET = '969ab6e04fcd44569331ed70aa6c7026'

# URLs de Spotify
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1'

# Variable global para cache del token
_token_cache = {
    'access_token': None,
    'expiry': None
}

def get_access_token():
    """
    Obtener token de acceso de Spotify usando Client Credentials Flow.
    Cache en memoria para evitar requests innecesarios.
    """
    # Verificar si tenemos un token en cache y aún válido
    if _token_cache['access_token'] and _token_cache['expiry']:
        if datetime.now() < _token_cache['expiry']:
            print("✅ Usando token en cache")
            return _token_cache['access_token']
    
    print("🔄 Solicitando nuevo token...")
    
    # Crear credenciales en base64
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    # Solicitar token
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data, timeout=10)
        
        print(f"📡 Token request status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error al obtener token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        token_data = response.json()
        access_token = token_data['access_token']
        expires_in = token_data['expires_in']
        
        # Guardar en cache (restar 60 segundos para seguridad)
        _token_cache['access_token'] = access_token
        _token_cache['expiry'] = datetime.now() + timedelta(seconds=expires_in - 60)
        
        print(f"✅ Token obtenido exitosamente: {access_token[:20]}...")
        return access_token
        
    except Exception as e:
        print(f"❌ Error al obtener token: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/')
def index():
    return render_template('spotify.html')

@app.route('/api/spotify/buscar')
def buscar_spotify():
    """Buscar canciones, artistas, álbumes o playlists"""
    query = request.args.get('q', '')
    tipo = request.args.get('tipo', 'track')
    limite = int(request.args.get('limite', 10))
    
    print(f"\n{'='*60}")
    print(f"🔍 Nueva búsqueda recibida")
    print(f"Query: '{query}'")
    print(f"Tipo: {tipo}")
    print(f"Límite: {limite} (type: {type(limite)})")
    print(f"{'='*60}")
    
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    token = get_access_token()
    
    if not token:
        print("❌ No se pudo obtener token")
        return jsonify({'error': 'Error al autenticar con Spotify'}), 500
    
    try:
        url = f'{SPOTIFY_API_URL}/search'
        headers = {'Authorization': f'Bearer {token}'}
        
        params = {
            'q': str(query),
            'type': str(tipo),
            'limit': int(limite),
            'market': 'MX'
        }
        
        print(f"📡 Haciendo request a Spotify...")
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error de Spotify:")
            print(response.text)
            return jsonify({
                'error': f'Error de Spotify API: {response.status_code}',
                'details': response.text
            }), 500
        
        print(f"✅ Búsqueda exitosa")
        
        data = response.json()
        resultados = []
        
        # Procesar según el tipo
        if tipo == 'track':
            for track in data.get('tracks', {}).get('items', []):
                album = track.get('album', {})
                artists = track.get('artists', [])
                
                resultados.append({
                    'id': track.get('id'),
                    'nombre': track.get('name', 'Sin título'),
                    'artistas': [a.get('name', '') for a in artists],
                    'artista_principal': artists[0].get('name', '') if artists else '',
                    'album': album.get('name', 'Sin álbum'),
                    'imagen': album.get('images', [{}])[0].get('url') if album.get('images') else None,
                    'duracion_ms': track.get('duration_ms', 0),
                    'duracion': f"{track.get('duration_ms', 0) // 60000}:{(track.get('duration_ms', 0) % 60000) // 1000:02d}",
                    'preview_url': track.get('preview_url'),
                    'spotify_url': track.get('external_urls', {}).get('spotify', ''),
                    'popularidad': track.get('popularity', 0),
                    'explicito': track.get('explicit', False)
                })
        
        elif tipo == 'artist':
            for artist in data.get('artists', {}).get('items', []):
                resultados.append({
                    'id': artist.get('id'),
                    'nombre': artist.get('name', 'Sin nombre'),
                    'generos': artist.get('genres', []),
                    'popularidad': artist.get('popularity', 0),
                    'imagen': artist.get('images', [{}])[0].get('url') if artist.get('images') else None,
                    'seguidores': artist.get('followers', {}).get('total', 0),
                    'spotify_url': artist.get('external_urls', {}).get('spotify', '')
                })
        
        elif tipo == 'album':
            for album in data.get('albums', {}).get('items', []):
                artists = album.get('artists', [])
                
                resultados.append({
                    'id': album.get('id'),
                    'nombre': album.get('name', 'Sin título'),
                    'artistas': [a.get('name', '') for a in artists],
                    'fecha_lanzamiento': album.get('release_date', ''),
                    'total_tracks': album.get('total_tracks', 0),
                    'imagen': album.get('images', [{}])[0].get('url') if album.get('images') else None,
                    'spotify_url': album.get('external_urls', {}).get('spotify', ''),
                    'tipo': album.get('album_type', 'album')
                })
        
        elif tipo == 'playlist':
            for playlist in data.get('playlists', {}).get('items', []):
                resultados.append({
                    'id': playlist.get('id'),
                    'nombre': playlist.get('name', 'Sin nombre'),
                    'descripcion': playlist.get('description', ''),
                    'owner': playlist.get('owner', {}).get('display_name', 'Desconocido'),
                    'total_tracks': playlist.get('tracks', {}).get('total', 0),
                    'imagen': playlist.get('images', [{}])[0].get('url') if playlist.get('images') else None,
                    'spotify_url': playlist.get('external_urls', {}).get('spotify', ''),
                    'publica': playlist.get('public', True)
                })
        
        print(f"✅ Se encontraron {len(resultados)} resultados")
        return jsonify(resultados)
        
    except Exception as e:
        print(f"❌ Error en buscar_spotify: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/spotify/artista/<artist_id>')
def info_artista(artist_id):
    """Obtener información completa de un artista"""
    print(f"\n🎤 Obteniendo info del artista: {artist_id}")
    
    token = get_access_token()
    if not token:
        return jsonify({'error': 'Error al autenticar'}), 500
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        
        # Información del artista
        artist_response = requests.get(
            f'{SPOTIFY_API_URL}/artists/{artist_id}',
            headers=headers,
            timeout=10
        )
        
        if artist_response.status_code != 200:
            print(f"❌ Error al obtener artista: {artist_response.status_code}")
            return jsonify({'error': 'Error al obtener información del artista'}), 500
            
        artist = artist_response.json()
        
        # Top tracks del artista
        top_response = requests.get(
            f'{SPOTIFY_API_URL}/artists/{artist_id}/top-tracks',
            headers=headers,
            params={'market': 'MX'},
            timeout=10
        )
        top_tracks = top_response.json().get('tracks', [])
        
        # Álbumes del artista
        albums_response = requests.get(
            f'{SPOTIFY_API_URL}/artists/{artist_id}/albums',
            headers=headers,
            params={'limit': 10, 'market': 'MX'},
            timeout=10
        )
        albums = albums_response.json().get('items', [])
        
        # Artistas relacionados
        related_response = requests.get(
            f'{SPOTIFY_API_URL}/artists/{artist_id}/related-artists',
            headers=headers,
            timeout=10
        )
        related = related_response.json().get('artists', [])
        
        resultado = {
            'id': artist['id'],
            'nombre': artist['name'],
            'generos': artist['genres'],
            'popularidad': artist['popularity'],
            'seguidores': artist['followers']['total'],
            'imagen': artist['images'][0]['url'] if artist['images'] else None,
            'spotify_url': artist['external_urls']['spotify'],
            'top_canciones': [
                {
                    'id': track['id'],
                    'nombre': track['name'],
                    'album': track['album']['name'],
                    'preview': track['preview_url'],
                    'imagen': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'duracion': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
                    'spotify_url': track['external_urls']['spotify']
                }
                for track in top_tracks[:10]
            ],
            'albums': [
                {
                    'id': album['id'],
                    'nombre': album['name'],
                    'fecha': album['release_date'],
                    'imagen': album['images'][0]['url'] if album['images'] else None,
                    'total_tracks': album['total_tracks'],
                    'tipo': album['album_type']
                }
                for album in albums
            ],
            'artistas_relacionados': [
                {
                    'id': rel['id'],
                    'nombre': rel['name'],
                    'imagen': rel['images'][0]['url'] if rel['images'] else None,
                    'popularidad': rel['popularity']
                }
                for rel in related[:6]
            ]
        }
        
        print(f"✅ Info del artista obtenida exitosamente")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Error en info_artista: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/spotify/album/<album_id>')
def info_album(album_id):
    """Obtener información de un álbum"""
    print(f"\n💿 Obteniendo info del álbum: {album_id}")
    
    token = get_access_token()
    if not token:
        return jsonify({'error': 'Error al autenticar'}), 500
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{SPOTIFY_API_URL}/albums/{album_id}',
            headers=headers,
            params={'market': 'MX'},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Error al obtener álbum: {response.status_code}")
            return jsonify({'error': 'Error al obtener información del álbum'}), 500
            
        album = response.json()
        
        resultado = {
            'id': album['id'],
            'nombre': album['name'],
            'artistas': [a['name'] for a in album['artists']],
            'fecha_lanzamiento': album['release_date'],
            'total_tracks': album['total_tracks'],
            'imagen': album['images'][0]['url'] if album['images'] else None,
            'generos': album['genres'],
            'sello': album['label'],
            'popularidad': album['popularity'],
            'spotify_url': album['external_urls']['spotify'],
            'tracks': [
                {
                    'numero': track['track_number'],
                    'nombre': track['name'],
                    'duracion': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
                    'preview': track['preview_url'],
                    'spotify_url': track['external_urls']['spotify']
                }
                for track in album['tracks']['items']
            ]
        }
        
        print(f"✅ Info del álbum obtenida exitosamente")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Error en info_album: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/spotify/recomendaciones')
def obtener_recomendaciones():
    """Obtener recomendaciones basadas en géneros"""
    generos = request.args.get('generos', 'pop,rock')
    limite = request.args.get('limite', 20, type=int)
    
    print(f"\n💡 Obteniendo recomendaciones: géneros={generos}")
    
    token = get_access_token()
    if not token:
        return jsonify({'error': 'Error al autenticar'}), 500
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{SPOTIFY_API_URL}/recommendations',
            headers=headers,
            params={
                'seed_genres': generos,
                'limit': limite,
                'market': 'MX'
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Error al obtener recomendaciones: {response.status_code}")
            return jsonify({'error': 'Error al obtener recomendaciones'}), 500
            
        data = response.json()
        
        recomendaciones = [
            {
                'id': track['id'],
                'nombre': track['name'],
                'artistas': [a['name'] for a in track['artists']],
                'album': track['album']['name'],
                'imagen': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'preview_url': track['preview_url'],
                'spotify_url': track['external_urls']['spotify']
            }
            for track in data.get('tracks', [])
        ]
        
        print(f"✅ {len(recomendaciones)} recomendaciones obtenidas")
        return jsonify(recomendaciones)
        
    except Exception as e:
        print(f"❌ Error en recomendaciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/spotify/generos')
def obtener_generos():
    """Obtener lista de géneros disponibles"""
    print(f"\n🎸 Obteniendo lista de géneros")
    
    token = get_access_token()
    if not token:
        return jsonify({'error': 'Error al autenticar'}), 500
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{SPOTIFY_API_URL}/recommendations/available-genre-seeds',
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Error al obtener géneros: {response.status_code}")
            return jsonify({'error': 'Error al obtener géneros'}), 500
            
        data = response.json()
        
        print(f"✅ {len(data.get('genres', []))} géneros obtenidos")
        return jsonify(data.get('genres', []))
        
    except Exception as e:
        print(f"❌ Error en obtener_generos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🎵 Buscador de Música - Spotify Web API")
    print("=" * 60)
    
    if CLIENT_ID == 'TU_CLIENT_ID_AQUI':
        print("⚠️  ADVERTENCIA: Credenciales no configuradas")
        print("   Obtén tus credenciales en:")
        print("   https://developer.spotify.com/dashboard")
    else:
        print(f"✅ Client ID configurado: {CLIENT_ID[:20]}...")
    
    print("🌐 Servidor corriendo en: http://127.0.0.1:5000")
    print("=" * 60)
    
    app.run(debug=True)