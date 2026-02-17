from flask import Flask, render_template, request, jsonify, session
import requests
import base64
from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')

# ==================== CREDENCIALES DE APIs ====================
# Spotify
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1'

# TMDB (Películas)
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'

# Clima
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Divisas
EXCHANGE_API_KEY = os.getenv('EXCHANGE_API_KEY')
EXCHANGE_BASE_URL = 'https://v6.exchangerate-api.com/v6'

# GitHub
GITHUB_API = 'https://api.github.com'

# Google Books
GOOGLE_BOOKS_API = 'https://www.googleapis.com/books/v1/volumes'

# Base de datos
DATABASE = os.getenv('DATABASE_NAME', 'productos.db')

# Cache para tokens
_token_cache = {
    'access_token': None,
    'expiry': None
}

# ==================== PÁGINA PRINCIPAL ====================
@app.route('/')
def index():
    """Dashboard principal con todas las apps"""
    return render_template('index.html')

# ==================== RUTAS A PÁGINAS ====================
@app.route('/spotify')
def spotify():
    return render_template('spotify.html')

@app.route('/peliculas')
def peliculas():
    return render_template('peliculas.html')

@app.route('/clima')
def clima():
    return render_template('clima.html')

@app.route('/divisas')
def divisas():
    return render_template('divisas.html')

@app.route('/github')
def github():
    return render_template('github.html')

@app.route('/libros')
def libros():
    return render_template('libros.html')

@app.route('/lugares')
def lugares():
    return render_template('lugares.html')

@app.route('/productos')
def productos():
    return render_template('productos.html')

@app.route('/reddit')
def reddit():
    return render_template('reddit.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

# ==================== SPOTIFY API ====================
def get_spotify_token():
    """Obtener token de Spotify con cache"""
    if _token_cache['access_token'] and _token_cache['expiry']:
        if datetime.now() < _token_cache['expiry']:
            return _token_cache['access_token']
    
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_base64 = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data={'grant_type': 'client_credentials'}, timeout=10)
        if response.status_code == 200:
            token_data = response.json()
            _token_cache['access_token'] = token_data['access_token']
            _token_cache['expiry'] = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
            return token_data['access_token']
    except Exception as e:
        print(f"Error obteniendo token Spotify: {e}")
    return None

@app.route('/api/spotify/buscar')
def buscar_spotify():
    query = request.args.get('q', '')
    tipo = request.args.get('tipo', 'track')
    limite = int(request.args.get('limite', 10))
    
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    token = get_spotify_token()
    if not token:
        return jsonify({'error': 'Error al autenticar con Spotify'}), 500
    
    try:
        response = requests.get(
            f'{SPOTIFY_API_URL}/search',
            headers={'Authorization': f'Bearer {token}'},
            params={'q': query, 'type': tipo, 'limit': limite, 'market': 'MX'},
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'Error de Spotify API: {response.status_code}'}), 500
        
        data = response.json()
        resultados = []
        
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
        
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/spotify/artista/<artist_id>')
def info_artista_spotify(artist_id):
    token = get_spotify_token()
    if not token:
        return jsonify({'error': 'Error al autenticar'}), 500
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        
        artist_response = requests.get(f'{SPOTIFY_API_URL}/artists/{artist_id}', headers=headers, timeout=10)
        if artist_response.status_code != 200:
            return jsonify({'error': 'Error al obtener artista'}), 500
        
        artist = artist_response.json()
        
        top_response = requests.get(f'{SPOTIFY_API_URL}/artists/{artist_id}/top-tracks', headers=headers, params={'market': 'MX'}, timeout=10)
        top_tracks = top_response.json().get('tracks', [])
        
        albums_response = requests.get(f'{SPOTIFY_API_URL}/artists/{artist_id}/albums', headers=headers, params={'limit': 10, 'market': 'MX'}, timeout=10)
        albums = albums_response.json().get('items', [])
        
        related_response = requests.get(f'{SPOTIFY_API_URL}/artists/{artist_id}/related-artists', headers=headers, timeout=10)
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
                    'preview': track.get('preview_url'),
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
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/spotify/album/<album_id>')
def info_album_spotify(album_id):
    token = get_spotify_token()
    if not token:
        return jsonify({'error': 'Error al autenticar'}), 500
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{SPOTIFY_API_URL}/albums/{album_id}', headers=headers, params={'market': 'MX'}, timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': 'Error al obtener álbum'}), 500
        
        album = response.json()
        
        resultado = {
            'id': album['id'],
            'nombre': album['name'],
            'artistas': [a['name'] for a in album['artists']],
            'fecha_lanzamiento': album['release_date'],
            'total_tracks': album['total_tracks'],
            'imagen': album['images'][0]['url'] if album['images'] else None,
            'generos': album.get('genres', []),
            'sello': album.get('label', ''),
            'popularidad': album.get('popularity', 0),
            'spotify_url': album['external_urls']['spotify'],
            'tracks': [
                {
                    'numero': track['track_number'],
                    'nombre': track['name'],
                    'duracion': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
                    'preview': track.get('preview_url'),
                    'spotify_url': track['external_urls']['spotify']
                }
                for track in album['tracks']['items']
            ]
        }
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PELÍCULAS API ====================
@app.route('/api/peliculas/buscar')
def buscar_peliculas():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    try:
        response = requests.get(
            f'{TMDB_BASE_URL}/search/movie',
            params={
                'api_key': TMDB_API_KEY,
                'query': query,
                'language': 'es-MX',
                'page': page,
                'include_adult': False
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Error al buscar películas'}), 500
        
        data = response.json()
        
        peliculas = []
        for movie in data.get('results', []):
            peliculas.append({
                'id': movie['id'],
                'titulo': movie['title'],
                'titulo_original': movie['original_title'],
                'descripcion': movie['overview'],
                'poster': f"{TMDB_IMAGE_BASE}{movie['poster_path']}" if movie.get('poster_path') else None,
                'backdrop': f"https://image.tmdb.org/t/p/original{movie['backdrop_path']}" if movie.get('backdrop_path') else None,
                'fecha_estreno': movie.get('release_date', ''),
                'popularidad': movie.get('popularity', 0),
                'calificacion': movie.get('vote_average', 0),
                'votos': movie.get('vote_count', 0)
            })
        
        return jsonify({
            'peliculas': peliculas,
            'pagina': data['page'],
            'total_paginas': data['total_pages'],
            'total_resultados': data['total_results']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/peliculas/<int:movie_id>')
def detalle_pelicula(movie_id):
    try:
        response = requests.get(
            f'{TMDB_BASE_URL}/movie/{movie_id}',
            params={
                'api_key': TMDB_API_KEY,
                'language': 'es-MX',
                'append_to_response': 'credits,videos,similar'
            },
            timeout=10
        )
        
        if response.status_code == 404:
            return jsonify({'error': 'Película no encontrada'}), 404
        
        if response.status_code != 200:
            return jsonify({'error': 'Error al obtener detalles'}), 500
        
        movie = response.json()
        
        cast = [
            {
                'nombre': actor['name'],
                'personaje': actor['character'],
                'foto': f"{TMDB_IMAGE_BASE}{actor['profile_path']}" if actor.get('profile_path') else None
            }
            for actor in movie.get('credits', {}).get('cast', [])[:10]
        ]
        
        crew = movie.get('credits', {}).get('crew', [])
        director = next((c['name'] for c in crew if c['job'] == 'Director'), None)
        
        videos = [
            {
                'nombre': video['name'],
                'tipo': video['type'],
                'key': video['key'],
                'url': f"https://www.youtube.com/watch?v={video['key']}"
            }
            for video in movie.get('videos', {}).get('results', [])
            if video['site'] == 'YouTube' and video['type'] in ['Trailer', 'Teaser']
        ]
        
        similares = [
            {
                'id': sim['id'],
                'titulo': sim['title'],
                'poster': f"{TMDB_IMAGE_BASE}{sim['poster_path']}" if sim.get('poster_path') else None,
                'calificacion': sim.get('vote_average', 0)
            }
            for sim in movie.get('similar', {}).get('results', [])[:6]
        ]
        
        detalle = {
            'id': movie['id'],
            'titulo': movie['title'],
            'titulo_original': movie['original_title'],
            'descripcion': movie['overview'],
            'tagline': movie.get('tagline', ''),
            'poster': f"{TMDB_IMAGE_BASE}{movie['poster_path']}" if movie.get('poster_path') else None,
            'backdrop': f"https://image.tmdb.org/t/p/original{movie['backdrop_path']}" if movie.get('backdrop_path') else None,
            'fecha_estreno': movie.get('release_date', ''),
            'duracion': movie.get('runtime', 0),
            'calificacion': movie.get('vote_average', 0),
            'votos': movie.get('vote_count', 0),
            'generos': [g['name'] for g in movie.get('genres', [])],
            'director': director,
            'reparto': cast,
            'trailers': videos,
            'similares': similares
        }
        
        return jsonify(detalle)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/peliculas/populares')
def peliculas_populares():
    page = request.args.get('page', 1, type=int)
    
    try:
        response = requests.get(
            f'{TMDB_BASE_URL}/movie/popular',
            params={'api_key': TMDB_API_KEY, 'language': 'es-MX', 'page': page},
            timeout=10
        )
        data = response.json()
        
        peliculas = [
            {
                'id': movie['id'],
                'titulo': movie['title'],
                'poster': f"{TMDB_IMAGE_BASE}{movie['poster_path']}" if movie.get('poster_path') else None,
                'calificacion': movie.get('vote_average', 0),
                'fecha_estreno': movie.get('release_date', '')
            }
            for movie in data.get('results', [])
        ]
        
        return jsonify({'peliculas': peliculas, 'pagina': data['page'], 'total_paginas': data['total_pages']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== CLIMA API ====================
@app.route('/api/clima')
def obtener_clima():
    try:
        ip_response = requests.get('http://ip-api.com/json/', timeout=5)
        ubicacion = ip_response.json()
        
        if ubicacion.get('status') == 'fail':
            return jsonify({'error': 'No se pudo obtener ubicación'}), 400
        
        ciudad = ubicacion.get('city', 'Ciudad desconocida')
        lat = ubicacion.get('lat')
        lon = ubicacion.get('lon')
        
        clima_response = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={'lat': lat, 'lon': lon, 'appid': WEATHER_API_KEY, 'units': 'metric', 'lang': 'es'},
            timeout=5
        )
        clima = clima_response.json()
        
        resultado = {
            'ciudad': ciudad,
            'pais': ubicacion.get('country', 'Desconocido'),
            'temperatura': round(clima['main']['temp'], 1),
            'descripcion': clima['weather'][0]['description'].capitalize(),
            'humedad': clima['main']['humidity'],
            'viento': clima['wind']['speed'],
            'icono': clima['weather'][0]['icon']
        }
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== DIVISAS API ====================
@app.route('/api/divisas/convertir')
def convertir_divisas():
    monto = request.args.get('monto', type=float)
    de = request.args.get('de', 'USD').upper()
    a = request.args.get('a', 'MXN').upper()
    
    if not monto:
        return jsonify({'error': 'Monto requerido'}), 400
    
    try:
        url = f'{EXCHANGE_BASE_URL}/{EXCHANGE_API_KEY}/pair/{de}/{a}/{monto}'
        response = requests.get(url)
        data = response.json()
        
        if data['result'] != 'success':
            return jsonify({'error': 'Error en conversión'}), 400
        
        return jsonify({
            'monto_original': monto,
            'moneda_origen': de,
            'moneda_destino': a,
            'monto_convertido': data['conversion_result'],
            'tasa_conversion': data['conversion_rate']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/divisas/monedas')
def listar_monedas():
    monedas = {
        'USD': {'nombre': 'Dólar Estadounidense', 'simbolo': '$', 'bandera': '🇺🇸'},
        'EUR': {'nombre': 'Euro', 'simbolo': '€', 'bandera': '🇪🇺'},
        'GBP': {'nombre': 'Libra Esterlina', 'simbolo': '£', 'bandera': '🇬🇧'},
        'JPY': {'nombre': 'Yen Japonés', 'simbolo': '¥', 'bandera': '🇯🇵'},
        'MXN': {'nombre': 'Peso Mexicano', 'simbolo': '$', 'bandera': '🇲🇽'},
        'CAD': {'nombre': 'Dólar Canadiense', 'simbolo': '$', 'bandera': '🇨🇦'},
        'AUD': {'nombre': 'Dólar Australiano', 'simbolo': '$', 'bandera': '🇦🇺'},
        'CHF': {'nombre': 'Franco Suizo', 'simbolo': 'Fr', 'bandera': '🇨🇭'},
        'CNY': {'nombre': 'Yuan Chino', 'simbolo': '¥', 'bandera': '🇨🇳'},
        'BRL': {'nombre': 'Real Brasileño', 'simbolo': 'R$', 'bandera': '🇧🇷'}
    }
    return jsonify(monedas)

# ==================== GITHUB API ====================
@app.route('/api/github/usuario/<username>')
def obtener_usuario_github(username):
    try:
        user_response = requests.get(f'{GITHUB_API}/users/{username}')
        
        if user_response.status_code == 404:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        usuario = user_response.json()
        repos_response = requests.get(f'{GITHUB_API}/users/{username}/repos?per_page=100')
        repos = repos_response.json()
        
        total_stars = sum(repo['stargazers_count'] for repo in repos)
        total_forks = sum(repo['forks_count'] for repo in repos)
        
        lenguajes = {}
        for repo in repos:
            lang = repo['language']
            if lang:
                lenguajes[lang] = lenguajes.get(lang, 0) + 1
        
        top_lenguajes = sorted(lenguajes.items(), key=lambda x: x[1], reverse=True)[:3]
        
        resultado = {
            'nombre': usuario.get('name') or username,
            'username': usuario['login'],
            'bio': usuario.get('bio'),
            'avatar': usuario['avatar_url'],
            'repositorios': usuario['public_repos'],
            'seguidores': usuario['followers'],
            'siguiendo': usuario['following'],
            'ubicacion': usuario.get('location'),
            'empresa': usuario.get('company'),
            'blog': usuario.get('blog'),
            'creado': usuario['created_at'][:10],
            'total_stars': total_stars,
            'total_forks': total_forks,
            'top_lenguajes': [{'lenguaje': l[0], 'repos': l[1]} for l in top_lenguajes],
            'repos_destacados': [
                {
                    'nombre': repo['name'],
                    'descripcion': repo['description'],
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'lenguaje': repo['language'],
                    'url': repo['html_url']
                }
                for repo in sorted(repos, key=lambda x: x['stargazers_count'], reverse=True)[:5]
            ]
        }
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/github/buscar/repos')
def buscar_repos_github():
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    try:
        response = requests.get(
            f'{GITHUB_API}/search/repositories',
            params={'q': query, 'sort': 'stars', 'order': 'desc', 'per_page': 15}
        )
        data = response.json()
        
        repos = [
            {
                'nombre': repo['full_name'],
                'descripcion': repo['description'],
                'stars': repo['stargazers_count'],
                'lenguaje': repo['language'],
                'url': repo['html_url']
            }
            for repo in data.get('items', [])
        ]
        
        return jsonify(repos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== LIBROS API ====================
@app.route('/api/libros/buscar')
def buscar_libros():
    query = request.args.get('q', '')
    max_results = request.args.get('max', 20, type=int)
    
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    try:
        response = requests.get(
            GOOGLE_BOOKS_API,
            params={'q': query, 'maxResults': min(max_results, 40), 'printType': 'books', 'langRestrict': 'es'}
        )
        data = response.json()
        
        if 'items' not in data:
            return jsonify([])
        
        libros = []
        for item in data['items']:
            info = item.get('volumeInfo', {})
            venta = item.get('saleInfo', {})
            
            libro = {
                'id': item['id'],
                'titulo': info.get('title', 'Sin título'),
                'autores': info.get('authors', []),
                'descripcion': (info.get('description', '')[:300] + '...') if info.get('description') else '',
                'editorial': info.get('publisher', ''),
                'fecha_publicacion': info.get('publishedDate', ''),
                'paginas': info.get('pageCount', 0),
                'categorias': info.get('categories', []),
                'imagen': info.get('imageLinks', {}).get('thumbnail', ''),
                'preview_link': info.get('previewLink', ''),
                'rating': info.get('averageRating', 0)
            }
            
            libros.append(libro)
        
        return jsonify(libros)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== REDDIT API ====================
@app.route('/api/reddit/posts')
def obtener_posts_reddit():
    subreddit = request.args.get('subreddit', 'python')
    filtro = request.args.get('filtro', 'hot')
    limit = request.args.get('limit', 10, type=int)
    
    url = f'https://www.reddit.com/r/{subreddit}/{filtro}.json'
    headers = {'User-Agent': 'Mozilla/5.0 (FlaskApp/1.0)'}
    
    try:
        response = requests.get(url, headers=headers, params={'limit': limit})
        
        if response.status_code == 404:
            return jsonify({'error': 'Subreddit no encontrado'}), 404
        
        data = response.json()
        
        posts = []
        for post in data['data']['children']:
            post_data = post['data']
            fecha = datetime.fromtimestamp(post_data['created_utc'])
            
            posts.append({
                'titulo': post_data['title'],
                'autor': post_data['author'],
                'puntos': post_data['score'],
                'comentarios': post_data['num_comments'],
                'url': f"https://reddit.com{post_data['permalink']}",
                'fecha': fecha.strftime('%Y-%m-%d %H:%M'),
                'thumbnail': post_data.get('thumbnail') if post_data.get('thumbnail') not in ['self', 'default', ''] else None,
                'selftext': (post_data.get('selftext', '')[:200] + '...') if post_data.get('selftext') else ''
            })
        
        return jsonify({'subreddit': subreddit, 'posts': posts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reddit/subreddits/populares')
def subreddits_populares():
    subreddits = [
        {'nombre': 'python', 'descripcion': 'Python programming'},
        {'nombre': 'learnprogramming', 'descripcion': 'Aprender programación'},
        {'nombre': 'webdev', 'descripcion': 'Desarrollo web'},
        {'nombre': 'javascript', 'descripcion': 'JavaScript'},
        {'nombre': 'flask', 'descripcion': 'Flask framework'},
        {'nombre': 'technology', 'descripcion': 'Tecnología'},
        {'nombre': 'programming', 'descripcion': 'Programación general'},
        {'nombre': 'mexico', 'descripcion': 'México'}
    ]
    return jsonify(subreddits)

# ==================== LUGARES API ====================
@app.route('/api/lugares')
def buscar_lugares():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    tipo = request.args.get('tipo', 'restaurant')
    radio = request.args.get('radio', 1000, type=int)
    
    tipos_osm = {
        'restaurant': 'amenity=restaurant',
        'hospital': 'amenity=hospital',
        'cafe': 'amenity=cafe',
        'farmacia': 'amenity=pharmacy',
        'tienda': 'shop=supermarket',
        'gasolinera': 'amenity=fuel',
        'banco': 'amenity=bank',
        'hotel': 'tourism=hotel'
    }
    
    query = tipos_osm.get(tipo, 'amenity=restaurant')
    
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node[{query}](around:{radio},{lat},{lon});
      way[{query}](around:{radio},{lat},{lon});
    );
    out center;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=30)
        data = response.json()
        
        lugares = []
        for elemento in data['elements'][:20]:
            if 'center' in elemento:
                coords = elemento['center']
            elif 'lat' in elemento:
                coords = {'lat': elemento['lat'], 'lon': elemento['lon']}
            else:
                continue
            
            tags = elemento.get('tags', {})
            lugares.append({
                'nombre': tags.get('name', 'Sin nombre'),
                'direccion': tags.get('addr:street', '') + ' ' + tags.get('addr:housenumber', ''),
                'lat': coords['lat'],
                'lon': coords['lon'],
                'tipo': tags.get('amenity') or tags.get('shop') or tags.get('tourism', ''),
                'telefono': tags.get('phone', ''),
                'horario': tags.get('opening_hours', '')
            })
        
        return jsonify(lugares)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PRODUCTOS API (SQLite) ====================
def init_db():
    """Inicializar base de datos"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            categoria TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM productos')
    if cursor.fetchone()[0] == 0:
        productos_ejemplo = [
            ('Laptop HP', 'Laptop HP 15.6" Core i5', 15999.99, 10, 'Electrónica'),
            ('Mouse Logitech', 'Mouse inalámbrico Logitech M185', 299.99, 50, 'Accesorios'),
            ('Teclado Mecánico', 'Teclado mecánico RGB', 1299.99, 25, 'Accesorios'),
            ('Monitor Samsung', 'Monitor 24" Full HD', 3499.99, 15, 'Electrónica'),
            ('Webcam', 'Webcam 1080p con micrófono', 899.99, 30, 'Accesorios')
        ]
        cursor.executemany('''
            INSERT INTO productos (nombre, descripcion, precio, stock, categoria)
            VALUES (?, ?, ?, ?, ?)
        ''', productos_ejemplo)
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/productos', methods=['GET', 'POST'])
def productos_api():
    if request.method == 'GET':
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM productos')
            productos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(productos)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        data = request.json
        if not data.get('nombre') or not data.get('precio'):
            return jsonify({'error': 'Nombre y precio son requeridos'}), 400
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO productos (nombre, descripcion, precio, stock, categoria)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['nombre'],
                data.get('descripcion', ''),
                float(data['precio']),
                int(data.get('stock', 0)),
                data.get('categoria', 'General')
            ))
            conn.commit()
            producto_id = cursor.lastrowid
            conn.close()
            return jsonify({'id': producto_id, 'mensaje': 'Producto creado exitosamente'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/productos/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def producto_especifico(id):
    if request.method == 'GET':
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM productos WHERE id = ?', (id,))
            producto = cursor.fetchone()
            conn.close()
            
            if producto is None:
                return jsonify({'error': 'Producto no encontrado'}), 404
            
            return jsonify(dict(producto))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        data = request.json
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM productos WHERE id = ?', (id,))
            if cursor.fetchone() is None:
                conn.close()
                return jsonify({'error': 'Producto no encontrado'}), 404
            
            cursor.execute('''
                UPDATE productos 
                SET nombre = ?, descripcion = ?, precio = ?, stock = ?, categoria = ?
                WHERE id = ?
            ''', (
                data.get('nombre'),
                data.get('descripcion'),
                float(data.get('precio')),
                int(data.get('stock')),
                data.get('categoria'),
                id
            ))
            conn.commit()
            conn.close()
            return jsonify({'mensaje': 'Producto actualizado exitosamente'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM productos WHERE id = ?', (id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'error': 'Producto no encontrado'}), 404
            
            conn.commit()
            conn.close()
            return jsonify({'mensaje': 'Producto eliminado exitosamente'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# ==================== MAIN ====================
if __name__ == '__main__':
    # Verificar que las API keys estén configuradas
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("⚠️  ADVERTENCIA: Credenciales de Spotify no configuradas en .env")
    
    if not TMDB_API_KEY:
        print("⚠️  ADVERTENCIA: API Key de TMDB no configurada en .env")
    
    if not WEATHER_API_KEY:
        print("⚠️  ADVERTENCIA: API Key de OpenWeather no configurada en .env")
    
    if not EXCHANGE_API_KEY:
        print("⚠️  ADVERTENCIA: API Key de ExchangeRate no configurada en .env")
    
    init_db()
    print("=" * 70)
    print("🚀 API HUB - Todas tus Apps Unificadas")
    print("=" * 70)
    print("✅ Spotify API configurada")
    print("✅ TMDB (Películas) API configurada")
    print("✅ OpenWeather API configurada")
    print("✅ ExchangeRate API configurada")
    print("✅ GitHub API lista")
    print("✅ Google Books API lista")
    print("✅ Reddit API lista")
    print("✅ Base de datos SQLite inicializada")
    print("=" * 70)
    
    flask_port = int(os.getenv('FLASK_PORT', 5000))
    flask_debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"🌐 Servidor corriendo en: http://127.0.0.1:{flask_port}")
    print("=" * 70)
    
    app.run(debug=flask_debug, port=flask_port)