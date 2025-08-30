from flask import Flask, redirect, render_template, jsonify, request, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import random
from mysql.connector import connect, Error, pooling
import yaml
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import contextmanager

with open("config.yaml", "r") as f:
    conf = yaml.safe_load(f)

app = Flask(__name__)
app.config['SECRET_KEY'] = conf['SECRET_KEY']


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    user=conf['user'],
    password=conf['password'],
    host=conf['host_db'],
    database=conf['database']
)

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def get_id(self):
        return str(self.id)


def create_user_inventory(username):
    try:
        cnx = connect(user=conf['user'], password=conf['password'], 
                     host=conf['host_db'], database=conf['database'])
        cursor = cnx.cursor()
        
        # Создаем таблицу инвентаря для пользователя
        create_table = f"""
            CREATE TABLE IF NOT EXISTS inventory_{username} (
                user_id BIGINT NOT NULL,
                item_id INT NOT NULL,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, item_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (item_id) REFERENCES items(item_id)
            )
        """
        cursor.execute(create_table)
        cnx.commit()
        
    except Exception as e:
        print(f"Error creating inventory table: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()

@contextmanager
def get_cursor():
    conn = pool.get_connection()
    cur = conn.cursor(buffered=True)
    try:
        yield cur, conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@login_manager.user_loader
def load_user(user_id):
    cnx = connect(user=conf['user'], password=conf['password'], host=conf['host_db'], database=conf['database'])    
    cursor = cnx.cursor(buffered=True)
    select_user = f"""SELECT * FROM users WHERE user_id={user_id}"""
    cursor.execute(select_user)
    user_data = cursor.fetchall()
    return User(user_data[0][0], user_data[0][1], user_data[0][1])


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/spin")
@login_required
def spin():
    random_number = random.randint(1, 50)
    random_color = random.randint(1, 10)
    random_back = random.randint(1, 10)
    final_color = 0
    final_back = 0
    try:
        try:
            cnx = connect(user=conf['user'], password=conf['password'], 
                            host=conf['host_db'], database=conf['database'])
            cursor = cnx.cursor(buffered=True)
            select_rate = "SELECT rate FROM colors WHERE color_id = %s LIMIT 1"
            cursor.execute(select_rate, (random_color,))
            c_row = cursor.fetchone()
        except:
            return jsonify({'error': 'cant connect to db'})
        reroll = random.randint(c_row[0], 10)
        if reroll >= 5:
            double_reroll = random.randint(1, reroll)
            final_color = double_reroll
        else:
            final_color = reroll
        
        select_rate = "SELECT rate FROM backs WHERE back_id = %s LIMIT 1"
        cursor.execute(select_rate, (random_back,))
        b_row = cursor.fetchone()
        reroll = random.randint(b_row[0], 10)
        if reroll >= 5:
            double_reroll = random.randint(1, reroll)
            final_back = double_reroll
        else:
            final_back = reroll
    except:
        return jsonify({'error': 'some error'})
    # Сохраняем выпавший айтем в инвентарь пользователя
    color_rareness = c_row[0] / 100
    back_rareness = b_row[0] / 100
    if isinstance(random_number, int):
        all_rareness = (c_row[0] * b_row[0]) / 100
    else:
        all_rareness = (c_row[0] * b_row[0]) / 200
    try:
        cnx = connect(user=conf['user'], password=conf['password'], 
                        host=conf['host_db'], database=conf['database'])
        cursor = cnx.cursor(buffered=True)
        # Сохраняем предмет в инвентарь пользователя
        add_item = """
            INSERT INTO items (number, u_id, c_id, b_id, color_rareness, back_rareness, all_rareness) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """ 
        cursor.execute(add_item, (
            random_number,
            current_user.id,  # Используем current_user из Flask-Login
            final_color, 
            final_back, 
            round(color_rareness, 2),  # Округляем до 2 знаков
            round(back_rareness, 2),   # Округляем до 2 знаков
            round(all_rareness, 2)     # Округляем до 2 знаков
        ))
        
        cnx.commit()  # Не забываем коммитить изменения

        item_id = cursor.lastrowid
        
        # Сохраняем в инвентарь пользователя
        add_to_inventory = f"""
            INSERT INTO inventory_{current_user.username} (user_id, item_id)
            VALUES (%s, %s)
        """
        cursor.execute(add_to_inventory, (current_user.id, item_id))
        
        cnx.commit()
        
        return jsonify({
            'number': random_number,
            'color': final_color,
            'back': final_back,
            'rareness': {
                'color': round(color_rareness, 2),
                'back': round(back_rareness, 2),
                'all': round(all_rareness, 2)
            },
            'item_id': item_id
        })
        
    except Exception as e:
        print(f"Error in /spin: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()


@app.route("/signin", methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Отсутствуют данные'}), 400
        
        uname = data.get('username')
        upass = data.get('password')
        
        # Валидация входных данных
        if not uname or not upass:
            return jsonify({'success': False, 'message': 'Необходимо указать имя пользователя и пароль'}), 400
        
        if len(uname) < 3:
            return jsonify({'success': False, 'message': 'Имя пользователя должно содержать не менее 3 символов'}), 400
        
        if len(upass) < 6:
            return jsonify({'success': False, 'message': 'Пароль должен содержать не менее 6 символов'}), 400
        
        # Исправляем метод хеширования
        hashed_password = generate_password_hash(upass)
        
        try:
            with get_cursor() as (cur, conn):
                # Проверяем, существует ли пользователь
                cur.execute("SELECT user_id FROM users WHERE user_name = %s", (uname,))
                if cur.fetchone():
                    return jsonify({'success': False, 'message': 'Пользователь уже существует'}), 400
                
                # Добавляем нового пользователя
                cur.execute(
                    "INSERT INTO users (user_name, user_password) VALUES (%s, %s)",
                    (uname, hashed_password)
                )
                create_user_inventory(uname)
                return jsonify({'success': True, 'message': 'Пользователь успешно зарегистрирован'}), 201
        
        except Exception as e:
            # Логируем ошибку с деталями
            import traceback
            error_details = traceback.format_exc()
            print(f"Ошибка при регистрации пользователя: {e}")
            print(f"Детали ошибки: {error_details}")
            return jsonify({'success': False, 'message': 'Ошибка при регистрации'}), 500
    else:
        return render_template("signin.html")


@app.route("/inventory")
@login_required
def inventory():
    try:
        cnx = connect(user=conf['user'], password=conf['password'], 
                     host=conf['host_db'], database=conf['database'])
        cursor = cnx.cursor(buffered=True)
        
        # Берем ВСЕ предметы пользователя с названиями цветов и фонов
        select_items = """
            SELECT i.item_id, i.number, i.c_id, i.b_id, i.color_rareness, i.back_rareness, i.all_rareness,
                   c.name as color_name, c.code as color_code,
                   b.name as back_name, b.code as back_code
            FROM items i
            JOIN colors c ON i.c_id = c.color_id
            JOIN backs b ON i.b_id = b.back_id
            WHERE i.u_id = %s
            ORDER BY i.item_id
        """
        cursor.execute(select_items, (current_user.id,))
        items = cursor.fetchall()
        
        result = []
        for item in items:
            result.append({
                'item_id': item[0],
                'number': item[1],
                'c_id': item[2],
                'b_id': item[3],
                'color_rareness': float(item[4]),
                'back_rareness': float(item[5]),
                'all_rareness': float(item[6]),
                'color_name': item[7],
                'color_code': item[8],
                'back_name': item[9],
                'back_code': item[10]
            })
        
        return jsonify({'items': result})
        
    except Exception as e:
        print(f"Error in /inventory: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Отсутствуют данные'}), 400
        
        uname = data.get('username')
        upass = data.get('password')
        
        try:
            cnx = connect(user=conf['user'], password=conf['password'], 
                         host=conf['host_db'], database=conf['database'])
            cursor = cnx.cursor(buffered=True)
            
            select_user = "SELECT user_id, user_name, user_password FROM users WHERE user_name = %s LIMIT 1"
            cursor.execute(select_user, (uname,))
            row = cursor.fetchone()
            
            if row is None:
                # Пользователь не найден
                return jsonify({'success': False, 'message': 'Неверные учетные данные'}), 401
            
            user_id, user_name, stored_hash = row

            # Проверяем пароль
            if not check_password_hash(stored_hash, upass):
                return jsonify({'success': False, 'message': 'Неверные учетные данные'}), 401

            # Пароль верный - авторизуем пользователя
            user = User(user_id, user_name, stored_hash)
            login_user(user)
            
            # Закрываем соединение с БД
            cursor.close()
            cnx.close()
            
            return jsonify({
                'success': True, 
                'message': 'Авторизация успешна',
                'redirect': '/'  # Добавляем URL для перенаправления
            }), 200
            
        except Exception as e:
            # Логируем ошибку
            print(f"Ошибка при авторизации: {e}")
            return jsonify({'success': False, 'message': 'Ошибка при авторизации'}), 500
    
    return render_template("login.html")


@app.route("/leaderboard/total")
def leaderboard_total():
    try:
        cnx = connect(user=conf['user'], password=conf['password'], 
                     host=conf['host_db'], database=conf['database'])
        cursor = cnx.cursor(buffered=True, dictionary=True)
        
        query = """
            SELECT u.user_name, 
                   COUNT(i.item_id) as total_items,
                   AVG(i.all_rareness) as avg_rarity
            FROM users u
            JOIN items i ON u.user_id = i.u_id
            GROUP BY u.user_id, u.user_name
            ORDER BY total_items DESC, avg_rarity DESC
            LIMIT 20
        """
        cursor.execute(query)
        players = cursor.fetchall()
        
        return jsonify({'players': players})
        
    except Exception as e:
        print(f"Error loading total leaderboard: {str(e)}")
        return jsonify({'error': 'Failed to load leaderboard'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()

@app.route("/leaderboard/legendary")
def leaderboard_legendary():
    try:
        cnx = connect(user=conf['user'], password=conf['password'], 
                     host=conf['host_db'], database=conf['database'])
        cursor = cnx.cursor(buffered=True, dictionary=True)
        
        query = """
            SELECT u.user_name, 
                   COUNT(i.item_id) as legendary_items,
                   AVG(i.all_rareness) as avg_rarity
            FROM users u
            JOIN items i ON u.user_id = i.u_id
            WHERE i.all_rareness >= 0.8  -- Легендарные предметы
            GROUP BY u.user_id, u.user_name
            ORDER BY legendary_items DESC, avg_rarity DESC
            LIMIT 20
        """
        cursor.execute(query)
        players = cursor.fetchall()
        
        return jsonify({'players': players})
        
    except Exception as e:
        print(f"Error loading legendary leaderboard: {str(e)}")
        return jsonify({'error': 'Failed to load leaderboard'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()


@app.route("/leaderboard")
def leadboard():
    return render_template("top.html")


@app.route("/logout")
@login_required
def logout():
    session.pop('username', None)
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

