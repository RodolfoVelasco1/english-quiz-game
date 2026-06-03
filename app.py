from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

QUESTIONS = [
    {"q": "Imagine Dragons are very famous. _______ favorite music is rock.", "options": ["A) His", "B) Her", "C) Their"], "correct": 2},
    {"q": "Look at Nicki Nicole. _______ favorite color is black.", "options": ["A) Her", "B) His", "C) Their"], "correct": 0},
    {"q": "A: What is _______ Instagram username?\nB: Their username is @laberisooficial.", "options": ["A) his", "B) their", "C) her"], "correct": 1},
    {"q": "Milo J is a very famous singer. _______ favorite food is pizza.", "options": ["A) Her", "B) Their", "C) His"], "correct": 2},
    {"q": "A: What is Wos and Trueno's favorite music?\nB: _______ favorite music is rap.", "options": ["A) Their", "B) His", "C) Her"], "correct": 0},
    {"q": "A: What are _______ names?\nB: Their names are Nico and Facu.", "options": ["A) his", "B) her", "C) their"], "correct": 2},
    {"q": "Emilia likes pop, but Tiago PZK and Paulo Londra like trap. _______ favorite music is trap.", "options": ["A) Their", "B) Her", "C) His"], "correct": 0},
    {"q": "A: What is _______ name?\nB: Her name is Taylor Swift.", "options": ["A) his", "B) their", "C) her"], "correct": 2},
    {"q": "Tyler and Josh are from the USA. _______ favorite food is tacos.", "options": ["A) Their", "B) His", "C) Her"], "correct": 0},
    {"q": "A: What is _______ favorite color?\nB: His favorite color is red.", "options": ["A) her", "B) his", "C) their"], "correct": 1},
    {"q": "A: Who are they?\nB: _______ names are Messi and De Paul.", "options": ["A) Their", "B) His", "C) Her"], "correct": 0},
    {"q": "Duki is from Argentina. _______ Instagram username is @duki.", "options": ["A) Their", "B) Her", "C) His"], "correct": 2},
    {"q": "A: What is Emilia's favorite food?\nB: _______ favorite food is pasta.", "options": ["A) His", "B) Their", "C) Her"], "correct": 2},
    {"q": "A: What is _______ favorite music?\nB: Their favorite music is Rock.", "options": ["A) her", "B) his", "C) their"], "correct": 2},
    {"q": "The streamers are playing a video game. _______ favorite game is GTA.", "options": ["A) His", "B) Her", "C) Their"], "correct": 2},
    {"q": "A: What is her Instagram username?\nB: _______ username is @mariabecerra.", "options": ["A) His", "B) Her", "C) Their"], "correct": 1},
    {"q": "I have two dogs in my house. _______ favorite food is meat.", "options": ["A) His", "B) Their", "C) Her"], "correct": 1},
    {"q": "A: _______ their favorite color?\nB: Their favorite color is blue.", "options": ["A) Where is", "B) How old is", "C) What is"], "correct": 2},
    {"q": "A: What is _______ name?\nB: His name is Dibu Martínez.", "options": ["A) his", "B) her", "C) their"], "correct": 0},
    {"q": "I like Coldplay! _______ favorite color is yellow.", "options": ["A) Their", "B) His", "C) Her"], "correct": 0}
]

games = {}

@app.route('/')
def index():
    return render_template('player.html')

@app.route('/host')
def host():
    return render_template('host.html')

@socketio.on('create_game')
def on_create():
    pin = str(random.randint(1000, 9999))
    games[pin] = {
        'players': {},
        'current_q': 0,
        'state': 'waiting',
        'start_time': 0,
        'time_limit': 20 # Tiempo por defecto
    }
    join_room(pin)
    emit('game_created', {'pin': pin})

@socketio.on('join_game')
def on_join(data):
    pin = data.get('pin')
    name = data.get('name')
    if pin in games and games[pin]['state'] == 'waiting':
        join_room(pin)
        games[pin]['players'][request.sid] = {'name': name, 'score': 0, 'last_points': 0, 'answered': False}
        players_list = [p['name'] for p in games[pin]['players'].values()]
        emit('players_update', players_list, room=pin)
        emit('join_success', to=request.sid)
    else:
        emit('error', {'msg': 'Invalid PIN or game already started'}, to=request.sid)

@socketio.on('start_game')
def on_start(data):
    pin = data['pin']
    if pin in games:
        games[pin]['current_q'] = 0
        games[pin]['time_limit'] = data.get('time_limit', 20) 
        send_question(pin)

@socketio.on('next_question')
def on_next(data):
    pin = data['pin']
    if pin in games:
        games[pin]['current_q'] += 1
        if 'time_limit' in data:
            games[pin]['time_limit'] = data['time_limit']
            
        if games[pin]['current_q'] < len(QUESTIONS):
            send_question(pin)
        else:
            end_game(pin)

def send_question(pin):
    games[pin]['state'] = 'playing'
    games[pin]['start_time'] = time.time()
    for sid in games[pin]['players']:
        games[pin]['players'][sid]['answered'] = False
        games[pin]['players'][sid]['last_points'] = 0
    
    q_data = QUESTIONS[games[pin]['current_q']]
    emit('new_question', {
        'q_num': games[pin]['current_q'] + 1,
        'total_q': len(QUESTIONS),
        'question': q_data['q'],
        'options': q_data['options'],
        'time_limit': games[pin]['time_limit']
    }, room=pin)

@socketio.on('submit_answer')
def on_answer(data):
    pin = data['pin']
    ans_idx = data['answer']
    sid = request.sid
    
    if pin in games and games[pin]['state'] == 'playing' and not games[pin]['players'][sid]['answered']:
        player = games[pin]['players'][sid]
        player['answered'] = True
        
        q_data = QUESTIONS[games[pin]['current_q']]
        if ans_idx == q_data['correct']:
            time_taken = time.time() - games[pin]['start_time']
            question_time = games[pin]['time_limit']
            descuento_por_segundo = 500 / question_time 
            points = max(500, int(1000 - (time_taken * descuento_por_segundo)))
            if points > 1000: points = 1000
            player['last_points'] = points
            player['score'] += points
        
        all_answered = all(p['answered'] for p in games[pin]['players'].values())
        if all_answered:
            emit('force_end_question', room=pin)

@socketio.on('end_question')
def on_end_question(data):
    pin = data['pin']
    if pin in games:
        games[pin]['state'] = 'leaderboard'
        
        sorted_players = sorted(games[pin]['players'].values(), key=lambda x: x['score'], reverse=True)
        leaderboard = [{"name": p['name'], "score": p['score']} for p in sorted_players]
        
        emit('show_leaderboard', leaderboard, room=pin)
        
        for sid, p in games[pin]['players'].items():
            emit('player_result', {'earned': p['last_points'], 'total': p['score']}, to=sid)

def end_game(pin):
    games[pin]['state'] = 'finished'
    sorted_players = sorted(games[pin]['players'].values(), key=lambda x: x['score'], reverse=True)
    leaderboard = [{"name": p['name'], "score": p['score']} for p in sorted_players]
    emit('game_over', leaderboard, room=pin)

@socketio.on('kick_player')
def on_kick(data):
    pin = data['pin']
    name_to_kick = data['name']
    if pin in games:
        sid_to_remove = None
        for sid, p in games[pin]['players'].items():
            if p['name'] == name_to_kick:
                sid_to_remove = sid
                break
        
        if sid_to_remove:
            del games[pin]['players'][sid_to_remove]
            emit('kicked', to=sid_to_remove)
            
            if games[pin]['state'] == 'waiting':
                players_list = [p['name'] for p in games[pin]['players'].values()]
                emit('players_update', players_list, room=pin)
            elif games[pin]['state'] == 'leaderboard':
                sorted_players = sorted(games[pin]['players'].values(), key=lambda x: x['score'], reverse=True)
                leaderboard = [{"name": p['name'], "score": p['score']} for p in sorted_players]
                emit('show_leaderboard', leaderboard, room=pin)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
