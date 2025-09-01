from flask import Flask, redirect, render_template, jsonify, request, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import random
from mysql.connector import connect, Error, pooling
import yaml

with open("config.yaml", "r") as f:
    conf = yaml.safe_load(f)
pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    user=conf['user'],
    password=conf['password'],
    host=conf['host_db'],
    database=conf['database']
)

def calc_random():
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
                   VALUES (%s, %s, %s, %s, %s, %s, %s) \
                   """
        cursor.execute(add_item, (
            random_number,
            current_user.id,  # Используем current_user из Flask-Login
            final_color,
            final_back,
            round(color_rareness, 2),  # Округляем до 2 знаков
            round(back_rareness, 2),  # Округляем до 2 знаков
            round(all_rareness, 2)  # Округляем до 2 знаков
        ))

        cnx.commit()

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